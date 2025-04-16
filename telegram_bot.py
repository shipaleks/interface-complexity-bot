#!/usr/bin/env python3
"""
UI Analysis Telegram Bot

This bot allows users to send a UI screenshot for analysis.
It will process the image and return a comprehensive analysis,
including a PDF report and heatmap visualization.
"""

import os
import sys
import logging
import asyncio
import tempfile
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from ui_analysis_pipeline import run_analysis_pipeline, process_base64_image

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the token from environment variable
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("No TELEGRAM_TOKEN found in environment variables!")
    sys.exit(1)

# Define constants
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

# Keep track of user states
user_states = {}

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Привет! Я бот для анализа интерфейсов. Отправьте мне скриншот интерфейса, и я проведу его анализ."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Отправьте мне скриншот интерфейса, и я проведу его анализ на сложность и юзабилити. "
        "Вы получите PDF-отчет с детальным анализом и рекомендациями."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos."""
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # Send initial response
    processing_message = await update.message.reply_text("Начинаю обработку скриншота...")
    
    try:
        # Get the largest photo
        photo_file = await update.message.photo[-1].get_file()
        temp_img_path = TEMP_DIR / f"screenshot_{user_id}.png"
        await photo_file.download_to_drive(temp_img_path)
        
        # Ask user if they want to provide additional info
        keyboard = [
            [
                InlineKeyboardButton("Продолжить без дополнительной информации", callback_data="skip_info"),
                InlineKeyboardButton("Предоставить информацию о назначении интерфейса", callback_data="provide_info"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Для более точного анализа, хотите ли вы предоставить дополнительную информацию о скриншоте?",
            reply_markup=reply_markup,
        )
        
        # Store the image path in user data for later use
        context.user_data["image_path"] = str(temp_img_path)
        context.user_data["processing_message"] = processing_message
        context.user_data["chat_id"] = chat_id
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке фотографии. Пожалуйста, попробуйте еще раз."
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "skip_info":
        await query.edit_message_text("Анализирую интерфейс без дополнительной информации...")
        await process_interface_analysis(update, context, additional_info=None)
    
    elif query.data == "provide_info":
        await query.edit_message_text(
            "Пожалуйста, опишите, для чего предназначен этот интерфейс и какие основные задачи выполняют пользователи. "
            "Отправьте ваш ответ как обычное текстовое сообщение."
        )
        context.user_data["awaiting_info"] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages, particularly for additional info about screenshots."""
    if context.user_data.get("awaiting_info"):
        additional_info = update.message.text
        context.user_data["awaiting_info"] = False
        await update.message.reply_text("Спасибо за информацию! Начинаю анализ интерфейса...")
        await process_interface_analysis(update, context, additional_info)
    else:
        await update.message.reply_text(
            "Отправьте мне скриншот интерфейса для анализа, или используйте /help для получения информации."
        )

async def process_interface_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, additional_info: str = None) -> None:
    """Process the interface analysis pipeline."""
    image_path = context.user_data.get("image_path")
    processing_message = context.user_data.get("processing_message")
    chat_id = context.user_data.get("chat_id")
    
    if not image_path:
        await update.effective_chat.send_message("Ошибка: изображение не найдено. Пожалуйста, отправьте скриншот снова.")
        return
    
    try:
        # Update processing message
        if processing_message:
            await processing_message.edit_text("Выполняю анализ интерфейса с помощью GPT-4.1... Это может занять некоторое время.")
        else:
            processing_message = await update.effective_chat.send_message(
                "Выполняю анализ интерфейса с помощью GPT-4.1... Это может занять некоторое время."
            )
        
        # Define output paths
        output_dir = TEMP_DIR / f"analysis_{chat_id}"
        output_dir.mkdir(exist_ok=True)
        
        gpt_output_path = output_dir / "gpt_analysis.json"
        gemini_output_path = output_dir / "gemini_coordinates.json"
        heatmap_path = output_dir / "heatmap.png"
        report_path = output_dir / "interface_analysis_report.tex"
        pdf_path = output_dir / "interface_analysis_report.pdf"
        
        # 1. Run GPT-4.1 analysis
        cmd = [
            "python", "analyze_interface.py",
            "--image", image_path,
            "--output", gpt_output_path
        ]
        
        if additional_info:
            cmd.extend(["--context", additional_info])
        
        await processing_message.edit_text("Выполняю анализ интерфейса с помощью GPT-4.1... Это может занять некоторое время.")
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"GPT analysis failed: {process.stderr}")
            await update.effective_chat.send_message(
                "Произошла ошибка при анализе интерфейса. Пожалуйста, попробуйте позже."
            )
            return
        
        # 2. Run Gemini coordinate extraction
        await processing_message.edit_text("Определяю координаты проблемных областей с помощью Gemini...")
        cmd = [
            "python", "get_coordinates.py",
            "--input", gpt_output_path,
            "--image", image_path,
            "--output", gemini_output_path
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Gemini coordinate extraction failed: {process.stderr}")
            await update.effective_chat.send_message(
                "Произошла ошибка при определении координат проблемных областей. Продолжаю анализ без них."
            )
        
        # 3. Generate heatmap
        await processing_message.edit_text("Создаю тепловую карту проблемных областей...")
        cmd = [
            "python", "generate_heatmap.py",
            "--coordinates", gemini_output_path,
            "--image", image_path,
            "--output", heatmap_path
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Heatmap generation failed: {process.stderr}")
            await update.effective_chat.send_message(
                "Произошла ошибка при создании тепловой карты. Продолжаю без неё."
            )
        
        # 4. Generate report and PDF
        await processing_message.edit_text("Генерирую PDF-отчет с анализом и рекомендациями...")
        cmd = [
            "python", "generate_report_v2.py",
            "--input", gpt_output_path,
            "--output", report_path,
            "--gemini-data", gemini_output_path,
            "--image", image_path,
            "--heatmap", heatmap_path,
            "--pdf"
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            logger.error(f"Report generation failed: {process.stderr}")
            await update.effective_chat.send_message(
                "Произошла ошибка при создании отчета. Отправляю частичные результаты."
            )
        
        # Send results back to the user
        await processing_message.edit_text("Анализ завершен! Отправляю результаты...")
        
        # Send overall score and summary
        with open(gpt_output_path, 'r') as f:
            import json
            analysis_data = json.load(f)
            overall_score = analysis_data.get("overallScore", {}).get("score", "N/A")
            overall_interpretation = analysis_data.get("overallScore", {}).get("interpretation", "Информация недоступна")
            
            summary_text = f"📊 Общая оценка сложности интерфейса: {overall_score}/100\n\n{overall_interpretation}"
            await update.effective_chat.send_message(summary_text)
        
        # Send heatmap if available
        if os.path.exists(heatmap_path):
            await update.effective_chat.send_photo(
                photo=open(heatmap_path, 'rb'),
                caption="🔥 Тепловая карта проблемных областей интерфейса"
            )
        
        # Send PDF report if available
        if os.path.exists(pdf_path):
            await update.effective_chat.send_document(
                document=open(pdf_path, 'rb'),
                filename="Анализ_интерфейса.pdf",
                caption="📑 Подробный отчет о сложности интерфейса с рекомендациями"
            )
        
        # Send final message
        await update.effective_chat.send_message(
            "Анализ завершен! Если у вас есть вопросы или вы хотите проанализировать другой интерфейс, отправьте новый скриншот."
        )
        
    except Exception as e:
        logger.error(f"Error in analysis pipeline: {e}")
        await update.effective_chat.send_message(
            "Произошла ошибка в процессе анализа. Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 