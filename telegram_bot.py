#!/usr/bin/env python3
"""
Telegram bot for UI analysis.

This bot accepts screenshots from users, optionally asks for context,
runs an analysis pipeline, and returns the results including
strategic interpretations, recommendations, PDF reports and heatmaps.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Custom modules
from analysis_pipeline import run_analysis_pipeline

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Define state machine for conversation flow
class AnalysisStates(StatesGroup):
    waiting_for_screenshot = State()
    waiting_for_context = State()
    waiting_for_userflows = State()
    analyzing = State()

# Ensure directories exist
os.makedirs("temp", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Command handlers
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle the /start command."""
    await message.answer(
        "Привет! Я бот для анализа UI/UX интерфейсов. "
        "Отправь мне скриншот интерфейса для анализа."
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle the /help command."""
    await message.answer(
        "Как использовать бота:\n"
        "1. Отправьте скриншот интерфейса\n"
        "2. Опционально опишите, что изображено на скриншоте\n"
        "3. Опционально опишите основные пользовательские сценарии\n"
        "4. Дождитесь результатов анализа\n\n"
        "Я проведу когнитивный анализ интерфейса и предоставлю:\n"
        "- Стратегическую интерпретацию проблем\n"
        "- Рекомендации по улучшению\n"
        "- PDF-отчет с детальным анализом\n"
        "- Тепловую карту проблемных зон\n\n"
        "Команды:\n"
        "/start - Начать взаимодействие\n"
        "/cancel - Отменить текущий анализ\n"
        "/help - Показать эту справку"
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Handle the /cancel command."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять. Отправьте скриншот для анализа.")
        return

    # Cancel state and inform user
    await state.clear()
    await message.answer("Анализ отменен. Отправьте скриншот, чтобы начать снова.")

# Message handlers
@router.message(lambda message: message.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Handle incoming photos (screenshots)."""
    # Add debug logging
    logger.info(f"Received photo message from user {message.from_user.id}")
    
    try:
        # Check if we're already in a state
        current_state = await state.get_state()
        logger.info(f"Current state: {current_state}")
        
        if current_state and current_state != "AnalysisStates:waiting_for_screenshot":
            await message.answer("У вас уже идет процесс анализа. Используйте /cancel для отмены.")
            return

        # Get the largest photo (best quality)
        photo = message.photo[-1]
        logger.info(f"Photo file_id: {photo.file_id}, file_size: {photo.file_size}")
        
        # Generate unique filename using user ID and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = message.from_user.id
        file_id = f"{user_id}_{timestamp}"
        
        # Path to save the screenshot
        screenshot_path = f"temp/{file_id}_input.png"
        logger.info(f"Saving screenshot to: {screenshot_path}")
        
        # Ensure temp directory exists
        os.makedirs("temp", exist_ok=True)
        
        # Download the photo
        await message.answer("Получил скриншот! Сохраняю...")
        file_info = await bot.get_file(photo.file_id)
        logger.info(f"Got file info: {file_info.file_path}")
        
        await bot.download_file(file_info.file_path, screenshot_path)
        logger.info(f"Screenshot saved to: {screenshot_path}")
        
        # Save file path and info in FSM storage
        await state.update_data(
            screenshot_path=screenshot_path,
            file_id=file_id,
            timestamp=timestamp
        )
        logger.info(f"State data updated with screenshot path and file_id")
        
        # Move to the next state and ask for context
        await state.set_state(AnalysisStates.waiting_for_context)
        logger.info(f"State set to: AnalysisStates.waiting_for_context")
        
        await message.answer(
            "Что изображено на скриншоте? (опишите кратко или введите 'пропустить')"
        )
        logger.info(f"Sent prompt for context to user")
    except Exception as e:
        logger.error(f"Error in handle_photo: {e}", exc_info=True)
        await message.answer(f"Произошла ошибка при обработке изображения: {str(e)}")
        # Clear state on error
        await state.clear()

@router.message(AnalysisStates.waiting_for_context)
async def handle_context(message: Message, state: FSMContext):
    """Handle context description from user."""
    try:
        logger.info(f"Received context message from user {message.from_user.id}")
        context = message.text.strip()
        
        # Check if user wants to skip
        if context.lower() in ["пропустить", "skip", "-"]:
            context = None
            logger.info("User skipped context input")
        else:
            logger.info(f"Context received: {context[:50]}...")
        
        # Save context in FSM storage
        await state.update_data(context=context)
        logger.info("Context saved to state")
        
        # Move to the next state and ask for user flows
        await state.set_state(AnalysisStates.waiting_for_userflows)
        logger.info(f"State set to: AnalysisStates.waiting_for_userflows")
        
        await message.answer(
            "Какие основные пользовательские сценарии (user flows) связаны с этим экраном? "
            "(опишите кратко или введите 'пропустить')"
        )
        logger.info("Sent prompt for userflows to user")
    except Exception as e:
        logger.error(f"Error in handle_context: {e}", exc_info=True)
        await message.answer(f"Произошла ошибка при обработке контекста: {str(e)}")
        # Don't clear state, allow retry

@router.message(AnalysisStates.waiting_for_userflows)
async def handle_userflows(message: Message, state: FSMContext):
    """Handle user flows description from user and start analysis."""
    try:
        logger.info(f"Received userflows message from user {message.from_user.id}")
        userflows = message.text.strip()
        
        # Check if user wants to skip
        if userflows.lower() in ["пропустить", "skip", "-"]:
            userflows = None
            logger.info("User skipped userflows input")
        else:
            logger.info(f"Userflows received: {userflows[:50]}...")
        
        # Save user flows in FSM storage
        await state.update_data(userflows=userflows)
        logger.info("Userflows saved to state")
        
        # Get all the data we've collected
        data = await state.get_data()
        logger.info(f"Retrieved state data: {list(data.keys())}")
        
        screenshot_path = data["screenshot_path"]
        file_id = data["file_id"]
        context = data.get("context")
        userflows = data.get("userflows")
        
        # Move to analyzing state
        await state.set_state(AnalysisStates.analyzing)
        logger.info(f"State set to: AnalysisStates.analyzing")
        
        # Inform the user that analysis has started
        await message.answer(
            "Спасибо! Начинаю анализ интерфейса. "
            "Это может занять несколько минут..."
        )
        logger.info("Sent analysis start message to user")
        
        # Start the analysis pipeline in a separate task to not block the bot
        logger.info(f"Creating analysis task for file_id: {file_id}")
        asyncio.create_task(
            process_analysis(message, state, screenshot_path, file_id, context, userflows)
        )
    except Exception as e:
        logger.error(f"Error in handle_userflows: {e}", exc_info=True)
        await message.answer(f"Произошла ошибка при запуске анализа: {str(e)}")
        # Clear state on error
        await state.clear()

async def process_analysis(message, state, screenshot_path, file_id, context, userflows):
    """Process the analysis pipeline and send results to user."""
    try:
        logger.info(f"Starting analysis process for file_id: {file_id}")
        
        # Run the analysis pipeline
        await message.answer("⏳ Анализирую скриншот с помощью GPT-4.1...")
        logger.info("Sent GPT analysis start message to user")
        
        # Verify the screenshot file exists
        if not os.path.exists(screenshot_path):
            logger.error(f"Screenshot file not found at path: {screenshot_path}")
            await message.answer(f"❌ Ошибка: Файл скриншота не найден. Возможно, он был удален или не сохранен корректно.")
            await state.clear()
            return
            
        logger.info(f"Verified screenshot exists at: {screenshot_path}")
        
        # Call the analysis pipeline
        logger.info(f"Calling run_analysis_pipeline with screenshot: {screenshot_path}")
        results = await run_analysis_pipeline(
            screenshot_path=screenshot_path,
            file_id=file_id,
            context=context,
            userflows=userflows
        )
        
        if not results:
            logger.error(f"Analysis pipeline returned None for file_id: {file_id}")
            await message.answer("❌ Произошла ошибка при анализе. Пожалуйста, попробуйте позже или с другим скриншотом.")
            await state.clear()
            return
            
        logger.info(f"Analysis pipeline completed successfully with results: {list(results.keys())}")
            
        # Extract paths from results
        interpretation_path = results["interpretation_path"]
        recommendations_path = results["recommendations_path"]
        pdf_report_path = results["pdf_report_path"]
        heatmap_path = results["heatmap_path"]
        
        # Verify result files exist
        all_files_exist = True
        for path, label in [
            (interpretation_path, "interpretation"), 
            (recommendations_path, "recommendations"),
            (pdf_report_path, "PDF report"),
            (heatmap_path, "heatmap")
        ]:
            if not os.path.exists(path):
                logger.error(f"{label} file not found at path: {path}")
                all_files_exist = False
                
        if not all_files_exist:
            logger.warning("Some result files are missing")
            await message.answer("⚠️ Некоторые файлы результатов отсутствуют, но я продолжу обработку доступных данных.")
        
        # Send interpretation
        await message.answer("✅ Анализ завершен! Отправляю результаты...")
        logger.info("Sent analysis completion message to user")
        
        # Format and send interpretation
        if os.path.exists(interpretation_path):
            logger.info(f"Sending interpretation from: {interpretation_path}")
            await message.answer("🧠 <b>Стратегическая интерпретация:</b>")
            interpretation_messages = format_interpretation(interpretation_path)
            for msg in interpretation_messages:
                await message.answer(msg, parse_mode="HTML")
            logger.info(f"Sent {len(interpretation_messages)} interpretation messages")
        else:
            await message.answer("❌ Не удалось сформировать стратегическую интерпретацию.")
        
        # Format and send recommendations
        if os.path.exists(recommendations_path):
            logger.info(f"Sending recommendations from: {recommendations_path}")
            await message.answer("💡 <b>Стратегические рекомендации:</b>")
            recommendation_messages = format_recommendations(recommendations_path)
            for msg in recommendation_messages:
                await message.answer(msg, parse_mode="HTML")
            logger.info(f"Sent {len(recommendation_messages)} recommendation messages")
        else:
            await message.answer("❌ Не удалось сформировать стратегические рекомендации.")
        
        # Send PDF report
        if os.path.exists(pdf_report_path):
            logger.info(f"Sending PDF report: {pdf_report_path}")
            await message.answer("📊 <b>Полный отчет (PDF):</b>")
            pdf_file = FSInputFile(pdf_report_path)
            await message.answer_document(pdf_file, caption="Полный отчет с анализом интерфейса")
            logger.info("PDF report sent")
        else:
            await message.answer("❌ Не удалось сформировать PDF-отчет.")
        
        # Send heatmap
        if os.path.exists(heatmap_path):
            logger.info(f"Sending heatmap: {heatmap_path}")
            await message.answer("🔥 <b>Тепловая карта проблемных зон:</b>")
            heatmap_file = FSInputFile(heatmap_path)
            await message.answer_photo(heatmap_file, caption="Визуализация проблемных зон интерфейса")
            logger.info("Heatmap sent")
        else:
            await message.answer("❌ Не удалось сформировать тепловую карту.")
        
        # Complete the analysis process
        await message.answer(
            "Анализ завершен! Если у вас есть еще скриншоты для анализа, просто отправьте их."
        )
        logger.info(f"Analysis process completed for file_id: {file_id}")
        
    except Exception as e:
        logger.error(f"Error in process_analysis for file_id {file_id}: {e}", exc_info=True)
        await message.answer(
            f"❌ Произошла ошибка при обработке результатов: {str(e)}\n"
            "Пожалуйста, попробуйте позже или с другим скриншотом."
        )
    finally:
        # Clear the state regardless of success or failure
        await state.clear()
        logger.info(f"State cleared for file_id: {file_id}")

def format_interpretation(interpretation_path):
    """Format interpretation JSON into readable messages."""
    try:
        with open(interpretation_path, 'r', encoding='utf-8') as f:
            data = f.read()
            
        # Handle case when JSON is returned directly
        try:
            interpretation = json.loads(data)
        except json.JSONDecodeError:
            # Try to extract JSON from text if it's wrapped in backticks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', data, re.DOTALL)
            if json_match:
                try:
                    interpretation = json.loads(json_match.group(1))
                except:
                    return [f"Ошибка при парсинге JSON из интерпретации. Пожалуйста, проверьте файл: {interpretation_path}"]
            else:
                # If not JSON, return the raw text split into chunks
                return [data[i:i+4000] for i in range(0, len(data), 4000)]
        
        # Extract and format each section of the interpretation
        formatted_messages = []
        
        if 'strategicInterpretation' in interpretation:
            interp = interpretation['strategicInterpretation']
            
            # Cognitive Ecosystem
            if 'cognitiveEcosystem' in interp:
                formatted_messages.append(f"<b>🧬 Когнитивная Экосистема</b>\n\n{interp['cognitiveEcosystem']}")
            
            # Business-User Tension
            if 'businessUserTension' in interp:
                formatted_messages.append(f"<b>⚖️ Напряжение Бизнес-Пользователь</b>\n\n{interp['businessUserTension']}")
            
            # Attention Architecture
            if 'attentionArchitecture' in interp:
                formatted_messages.append(f"<b>👁️ Архитектура Внимания</b>\n\n{interp['attentionArchitecture']}")
            
            # Perceptual Crossroads
            if 'perceptualCrossroads' in interp:
                formatted_messages.append(f"<b>🔀 Перцептивные Перекрестки</b>\n\n{interp['perceptualCrossroads']}")
            
            # Hidden Patterns
            if 'hiddenPatterns' in interp:
                formatted_messages.append(f"<b>🔍 Скрытые Паттерны</b>\n\n{interp['hiddenPatterns']}")
        else:
            # If structure is not as expected, return raw JSON
            formatted_messages.append(f"Структура интерпретации не соответствует ожидаемой. Сырые данные:\n\n{data[:3900]}...")
            
        return formatted_messages
            
    except Exception as e:
        logger.error(f"Error formatting interpretation: {e}", exc_info=True)
        return [f"Ошибка при форматировании интерпретации: {str(e)}"]

def format_recommendations(recommendations_path):
    """Format recommendations JSON into readable messages."""
    try:
        with open(recommendations_path, 'r', encoding='utf-8') as f:
            data = f.read()
            
        # Handle case when JSON is returned directly
        try:
            recommendations = json.loads(data)
        except json.JSONDecodeError:
            # Try to extract JSON from text if it's wrapped in backticks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', data, re.DOTALL)
            if json_match:
                try:
                    recommendations = json.loads(json_match.group(1))
                except:
                    return [f"Ошибка при парсинге JSON из рекомендаций. Пожалуйста, проверьте файл: {recommendations_path}"]
            else:
                # If not JSON, return the raw text split into chunks
                return [data[i:i+4000] for i in range(0, len(data), 4000)]
        
        # Extract and format each recommendation
        formatted_messages = []
        
        if 'strategicRecommendations' in recommendations:
            for i, rec in enumerate(recommendations['strategicRecommendations'], 1):
                msg = f"<b>💡 Рекомендация {i}: {rec.get('title', 'Без названия')}</b>\n\n"
                
                if 'problemStatement' in rec:
                    msg += f"<b>Проблема:</b>\n{rec['problemStatement']}\n\n"
                
                if 'solutionDescription' in rec:
                    msg += f"<b>Решение:</b>\n{rec['solutionDescription']}\n\n"
                
                if 'businessConstraints' in rec:
                    msg += f"<b>Бизнес-ограничения:</b>\n{rec['businessConstraints']}\n\n"
                
                if 'expectedImpact' in rec:
                    msg += f"<b>Ожидаемый эффект:</b>\n{rec['expectedImpact']}\n\n"
                
                if 'crossDomainExample' in rec:
                    msg += f"<b>Пример из другой области:</b>\n{rec['crossDomainExample']}\n\n"
                
                if 'testingApproach' in rec:
                    msg += f"<b>Подход к тестированию:</b>\n{rec['testingApproach']}"
                
                formatted_messages.append(msg)
        else:
            # If structure is not as expected, return raw JSON
            formatted_messages.append(f"Структура рекомендаций не соответствует ожидаемой. Сырые данные:\n\n{data[:3900]}...")
            
        return formatted_messages
            
    except Exception as e:
        logger.error(f"Error formatting recommendations: {e}", exc_info=True)
        return [f"Ошибка при форматировании рекомендаций: {str(e)}"]

# Register the router
dp.include_router(router)

async def main():
    try:
        # Skip pending updates
        logger.info("Starting bot, deleting previous webhook updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot startup failed: {e}", exc_info=True)
        raise  # Re-raise to show error in logs

if __name__ == "__main__":
    try:
        logger.info("Bot initialization started")
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True) 