#!/usr/bin/env python3
import os
import json
import logging
import asyncio
import tempfile
from typing import Dict, Any, List, Optional
import traceback
from datetime import datetime
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

# Configure logging before imports
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for API keys early and log their presence (not their values)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not set in the environment variables")
    raise ValueError("TELEGRAM_BOT_TOKEN is required")
else:
    logger.info("TELEGRAM_BOT_TOKEN is set")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set in the environment variables")
else:
    logger.info("OPENAI_API_KEY is set")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set in the environment variables")
else:
    logger.info("GEMINI_API_KEY is set")

try:
    # Try to import the analyzer after checking environment variables
    from analyze_ui import UIAnalyzer
    logger.info("UIAnalyzer imported successfully")
except Exception as e:
    logger.error(f"Error importing UIAnalyzer: {e}")
    logger.error(traceback.format_exc())
    raise

# Create output directory for analysis results
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
logger.info(f"Output directory: {OUTPUT_DIR}")

# Check if important directories exist
for subdir in ["images", "reports", "data"]:
    dir_path = os.path.join(OUTPUT_DIR, subdir)
    os.makedirs(dir_path, exist_ok=True)
    logger.info(f"Checking directory: {dir_path} - {'exists' if os.path.exists(dir_path) else 'created'}")

# Create analyzer
try:
    analyzer = UIAnalyzer(output_dir=OUTPUT_DIR)
    logger.info("UIAnalyzer created successfully")
except Exception as e:
    logger.error(f"Error creating UIAnalyzer: {e}")
    logger.error(traceback.format_exc())
    raise

# User context storage
user_context: Dict[int, Dict[str, Any]] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    try:
        welcome_message = (
            "👋 Hello! I'm the UI Complexity Analyzer Bot.\n\n"
            "I can analyze your user interface screenshots and provide detailed insights on their complexity and usability issues.\n\n"
            "Simply send me a screenshot of any UI, and I'll analyze it for problems across six dimensions of complexity:\n"
            "• Structural visual organization\n"
            "• Visual perceptual complexity\n"
            "• Typographic complexity\n"
            "• Information load\n"
            "• Cognitive load\n"
            "• Operational complexity\n\n"
            "Type /help for more information on how to use me."
        )
        
        await update.message.reply_text(welcome_message)
        
        # Reset user context
        if update.effective_user and update.effective_user.id:
            user_context[update.effective_user.id] = {}
            logger.info(f"User context reset for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        logger.error(traceback.format_exc())
        try:
            await update.message.reply_text("An error occurred while processing your request. Please try again later.")
        except:
            pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    try:
        help_message = (
            "📋 *UI Complexity Analyzer Bot Help*\n\n"
            "*How to use:*\n"
            "1. Send me a screenshot of the UI you want to analyze.\n"
            "2. Wait for the analysis to complete (usually takes 1-2 minutes).\n"
            "3. Review the comprehensive report I'll provide.\n\n"
            "*Available commands:*\n"
            "/start - Start or restart the bot\n"
            "/help - Show this help message\n"
            "/about - Learn about UI complexity analysis\n\n"
            "*Tips for better results:*\n"
            "• Send clear, high-resolution screenshots.\n"
            "• Include the entire interface in the screenshot.\n"
            "• For large interfaces, consider analyzing specific sections separately."
        )
        
        await update.message.reply_text(help_message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        logger.error(traceback.format_exc())
        try:
            await update.message.reply_text("An error occurred while processing your request. Please try again later.")
        except:
            pass

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send information about UI complexity analysis."""
    try:
        about_message = (
            "🔍 *Understanding UI Complexity Analysis*\n\n"
            "Interface complexity analysis evaluates how difficult a UI is to use and understand across six key dimensions:\n\n"
            "*1. Structural Visual Organization:* How well elements are arranged and aligned.\n"
            "*2. Visual Perceptual Complexity:* How visually busy or cluttered the interface appears.\n"
            "*3. Typographic Complexity:* How text elements are formatted and organized.\n"
            "*4. Information Load:* How much information is presented at once.\n"
            "*5. Cognitive Load:* How much mental effort is required to understand the interface.\n"
            "*6. Operational Complexity:* How easy it is to complete tasks using the interface.\n\n"
            "Each interface receives an overall complexity score (0-100) and individual scores for each dimension."
        )
        
        await update.message.reply_text(about_message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in about command: {e}")
        logger.error(traceback.format_exc())
        try:
            await update.message.reply_text("An error occurred while processing your request. Please try again later.")
        except:
            pass

async def process_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a screenshot sent by the user."""
    logger.info("PHOTO HANDLER CALLED - Starting to process photo")
    user_id = update.effective_user.id
    logger.info(f"Processing screenshot from user {user_id}")
    
    # Send processing message
    processing_message = None
    try:
        processing_message = await update.message.reply_text(
            "🔍 Processing your screenshot. This will take about 1-2 minutes..."
        )
        logger.info("Sent initial processing message")
        
        # Get the photo with the highest resolution
        if not update.message.photo:
            logger.error("No photos found in the message")
            await update.message.reply_text("No photos found in your message. Please send a screenshot image.")
            return
            
        photo = update.message.photo[-1]
        logger.info(f"Photo details: file_id={photo.file_id}, width={photo.width}, height={photo.height}")
        
        # Create a temporary directory for this user
        temp_dir = os.path.join(OUTPUT_DIR, "temp", f"user_{user_id}")
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created temp directory: {temp_dir}")
        
        try:
            # Download the photo
            logger.info("Starting photo download")
            try:
                photo_file = await context.bot.get_file(photo.file_id)
                logger.info(f"Got file info: {photo_file}")
                screenshot_path = os.path.join(temp_dir, f"screenshot_{photo.file_id}.jpg")
                await photo_file.download_to_drive(screenshot_path)
                logger.info(f"Photo downloaded to: {screenshot_path}")
                
                # Check if file exists and has content
                if os.path.exists(screenshot_path):
                    file_size = os.path.getsize(screenshot_path)
                    logger.info(f"Downloaded file size: {file_size} bytes")
                    if file_size == 0:
                        logger.error("Downloaded file is empty")
                        raise ValueError("Downloaded file is empty")
                else:
                    logger.error(f"Downloaded file doesn't exist: {screenshot_path}")
                    raise FileNotFoundError(f"Downloaded file not found: {screenshot_path}")
            except Exception as download_error:
                logger.error(f"Error downloading photo: {download_error}")
                logger.error(traceback.format_exc())
                if processing_message:
                    await processing_message.edit_text(
                        "❌ Error downloading your image. Please try again."
                    )
                return
            
            # Store the screenshot path in user context
            if user_id not in user_context:
                user_context[user_id] = {}
            user_context[user_id]['screenshot_path'] = screenshot_path
            
            # Прямой вызов анализа, минуя асинхронный запуск
            logger.info("Starting direct analysis of the screenshot")
            try:
                # Создаем анализатор UI
                from analyze_ui import UIAnalyzer
                analyzer = UIAnalyzer(output_dir=OUTPUT_DIR)
                logger.info(f"Created analyzer with output_dir={OUTPUT_DIR}")
                
                # Запускаем анализ
                results = await analyzer.analyze_screenshot(screenshot_path)
                logger.info("Analysis completed successfully")
                
                # Сохраняем результаты
                user_context[user_id]['analysis_results'] = results
                
                # Отправляем результаты
                await processing_message.edit_text("✅ Analysis complete! Preparing your results...")
                await send_initial_results(update, context, results)
                logger.info("Results sent to the user")
                
            except Exception as analyze_error:
                logger.error(f"Error in direct analysis: {analyze_error}")
                logger.error(traceback.format_exc())
                if processing_message:
                    await processing_message.edit_text(
                        f"❌ Analysis failed: {str(analyze_error)[:100]}... Please try again later."
                    )
                return
            
        except Exception as e:
            logger.error(f"Error processing screenshot: {e}")
            logger.error(traceback.format_exc())
            if os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up temp directory: {cleanup_error}")
            
            if processing_message:
                await processing_message.edit_text(
                    "❌ Sorry, an error occurred while processing your screenshot. Please try again later."
                )
                logger.info("Sent error message to user")
            
    except Exception as e:
        logger.error(f"Error in process_screenshot: {e}")
        logger.error(traceback.format_exc())
        try:
            if processing_message:
                await processing_message.edit_text(
                    "❌ Sorry, an error occurred while processing your screenshot. Please try again later."
                )
            else:
                await update.message.reply_text(
                    "❌ Sorry, an error occurred while processing your screenshot. Please try again later."
                )
        except Exception as reply_error:
            logger.error(f"Error sending reply: {reply_error}")

async def perform_analysis(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    screenshot_path: str, 
    processing_message: Any
) -> None:
    """Perform the UI analysis and send results."""
    logger.info(f"Starting analysis of {screenshot_path}")
    user_id = update.effective_user.id
    
    try:
        # Update message to show analysis is in progress
        try:
            await processing_message.edit_text(
                "⏳ Running GPT-4 analysis on your interface (this may take a minute)..."
            )
            logger.info("Updated message: GPT-4 analysis in progress")
        except Exception as msg_error:
            logger.error(f"Error updating processing message: {msg_error}")
        
        # Analyze screenshot
        logger.info("Calling analyze_screenshot method")
        results = await analyzer.analyze_screenshot(screenshot_path)
        logger.info("Analysis completed successfully")
        
        # Store results in user context
        if user_id not in user_context:
            user_context[user_id] = {}
        user_context[user_id]['analysis_results'] = results
        logger.info("Analysis results stored in user context")
        
        # Update processing message
        try:
            await processing_message.edit_text("✅ Analysis complete! Preparing your results...")
            logger.info("Updated message: Analysis complete")
        except Exception as msg_error:
            logger.error(f"Error updating processing message: {msg_error}")
        
        # Send initial results
        logger.info("Sending initial results")
        await send_initial_results(update, context, results)
        logger.info("Initial results sent")
        
    except Exception as e:
        logger.error(f"Error performing analysis: {e}")
        logger.error(traceback.format_exc())
        try:
            await processing_message.edit_text(
                "❌ Sorry, an error occurred while analyzing your screenshot. Please try again later."
            )
        except Exception as msg_error:
            logger.error(f"Error updating processing message: {msg_error}")
            try:
                await update.message.reply_text(
                    "❌ Sorry, an error occurred while analyzing your screenshot. Please try again later."
                )
            except Exception as reply_error:
                logger.error(f"Error sending reply: {reply_error}")

async def test_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command to verify analyze_ui is working"""
    try:
        await update.message.reply_text("Starting simple test of analyze_ui component...")
        
        # Create a simple test image
        test_output_dir = os.path.join(OUTPUT_DIR, "test")
        os.makedirs(test_output_dir, exist_ok=True)
        
        # Import necessary libraries
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a test image
        test_image = Image.new('RGB', (300, 200), color=(240, 240, 240))
        d = ImageDraw.Draw(test_image)
        d.rectangle([(10, 10), (290, 190)], outline=(200, 200, 200), width=2)
        d.text((150, 100), "Test UI", fill=(0, 0, 0), anchor="mm")
        
        test_image_path = os.path.join(test_output_dir, "test_image.png")
        test_image.save(test_image_path)
        
        await update.message.reply_text(f"Created test image at {test_image_path}")
        await update.message.reply_text("Testing simple API calls to make sure connections work...")
        
        # Test OpenAI connection
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            models = client.models.list()
            await update.message.reply_text(f"OpenAI connection successful. Available models: {len(models.data)}")
        except Exception as e:
            await update.message.reply_text(f"OpenAI connection failed: {str(e)}")
        
        # Test Gemini connection
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Исправление ошибки с генератором - конвертируем в список
            try:
                models = list(genai.list_models())
                await update.message.reply_text(f"Gemini connection successful. Available models: {len(models)}")
            except Exception as list_error:
                # Альтернативный подход, если list() не работает
                models_count = 0
                for _ in genai.list_models():
                    models_count += 1
                await update.message.reply_text(f"Gemini connection successful. Available models: {models_count}")
        except Exception as e:
            await update.message.reply_text(f"Gemini connection failed: {str(e)}")
        
        # Проверка файловой системы
        try:
            # Проверяем доступ к файловой системе
            test_file_path = os.path.join(test_output_dir, "test_write.txt")
            with open(test_file_path, "w") as f:
                f.write("Test write access")
            file_size = os.path.getsize(test_file_path)
            await update.message.reply_text(f"File system test: Success. Wrote {file_size} bytes to {test_file_path}")
        except Exception as fs_error:
            await update.message.reply_text(f"File system test failed: {str(fs_error)}")
        
        await update.message.reply_text("Tests completed")
        
    except Exception as e:
        logger.error(f"Error in test command: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(f"Test failed: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        logger.info(f"Button callback from user {user_id}, data: {data}")
        
        if data == "show_details":
            # Show more detailed analysis
            logger.info("User requested detailed analysis")
            if user_id in user_context and 'analysis_results' in user_context[user_id]:
                results = user_context[user_id]['analysis_results']
                await send_detailed_analysis(query, results)
            else:
                logger.warning(f"No analysis results found for user {user_id}")
                await query.message.reply_text("No analysis results found. Please send a screenshot first.")
        
        elif data == "show_recommendations":
            # Show recommendations
            logger.info("User requested recommendations")
            if user_id in user_context and 'analysis_results' in user_context[user_id]:
                results = user_context[user_id]['analysis_results']
                await send_recommendations(query, results)
            else:
                logger.warning(f"No analysis results found for user {user_id}")
                await query.message.reply_text("No analysis results found. Please send a screenshot first.")
        
        elif data == "send_report":
            # Send PDF report
            logger.info("User requested PDF report")
            if user_id in user_context and 'analysis_results' in user_context[user_id]:
                results = user_context[user_id]['analysis_results']
                await send_pdf_report(query, results)
            else:
                logger.warning(f"No analysis results found for user {user_id}")
                await query.message.reply_text("No analysis results found. Please send a screenshot first.")
        
        elif data == "send_heatmap":
            # Send heatmap
            logger.info("User requested heatmap")
            if user_id in user_context and 'analysis_results' in user_context[user_id]:
                results = user_context[user_id]['analysis_results']
                await send_heatmap(query, results)
            else:
                logger.warning(f"No analysis results found for user {user_id}")
                await query.message.reply_text("No analysis results found. Please send a screenshot first.")
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        logger.error(traceback.format_exc())
        try:
            await update.callback_query.message.reply_text("An error occurred processing your request.")
        except:
            pass

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages."""
    try:
        await update.message.reply_text(
            "Please send me a screenshot of a user interface to analyze. "
            "Text analysis is not supported at this time."
        )
    except Exception as e:
        logger.error(f"Error in text_message_handler: {e}")
        logger.error(traceback.format_exc())

async def send_initial_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: Dict[str, Any]) -> None:
    """Send initial analysis results to the user."""
    try:
        # Extract data
        overall_score = results.get('overall_score', 0)
        categories = results.get('categories', {})
        top_issues = results.get('top_issues', [])
        
        logger.info(f"Preparing initial results: overall_score={overall_score}, categories={len(categories)}, top_issues={len(top_issues)}")
        
        # Prepare message
        complexity_level = get_complexity_level(overall_score)
        
        message = (
            f"🔍 *UI COMPLEXITY ANALYSIS RESULTS*\n\n"
            f"*Overall Complexity Score:* {overall_score}/100 ({complexity_level})\n\n"
            f"*Category Scores:*\n"
        )
        
        # Add category scores
        for category, score in categories.items():
            message += f"• {category}: {score}/100\n"
        
        message += "\n*Top Issues:*\n"
        
        # Add top 3 issues
        for i, issue in enumerate(top_issues[:3], 1):
            severity = issue.get('severity', 0)
            name = issue.get('name', 'Unnamed issue')
            message += f"{i}. {name} (Severity: {severity}/100)\n"
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("📋 Detailed Analysis", callback_data="show_details"),
                InlineKeyboardButton("💡 Recommendations", callback_data="show_recommendations")
            ],
            [
                InlineKeyboardButton("📊 View Heatmap", callback_data="send_heatmap"),
                InlineKeyboardButton("📄 PDF Report", callback_data="send_report")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message with inline keyboard
        logger.info("Sending results message with buttons")
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # If we have a heatmap, send it
        heatmap_path = results.get('heatmap_path')
        if heatmap_path and os.path.exists(heatmap_path):
            logger.info(f"Sending heatmap from {heatmap_path}")
            await update.message.reply_photo(
                photo=open(heatmap_path, 'rb'),
                caption="🔥 Heatmap of UI complexity issues (red areas indicate problem regions)"
            )
        else:
            logger.warning(f"Heatmap not found or doesn't exist: {heatmap_path}")
        
    except Exception as e:
        logger.error(f"Error sending results: {e}")
        logger.error(traceback.format_exc())
        try:
            await update.message.reply_text(
                "❌ Sorry, an error occurred while preparing your results. The analysis was completed successfully, "
                "but we couldn't format the results properly."
            )
        except Exception as reply_error:
            logger.error(f"Error sending reply: {reply_error}")

async def send_detailed_analysis(query, results: Dict[str, Any]) -> None:
    """Send detailed analysis to the user."""
    try:
        top_issues = results.get('top_issues', [])
        
        message = "*📋 DETAILED ANALYSIS*\n\n"
        
        # Show all top issues
        for i, issue in enumerate(top_issues, 1):
            severity = issue.get('severity', 0)
            name = issue.get('name', 'Unnamed issue')
            category = issue.get('category', 'Other')
            description = issue.get('description', '')
            
            message += f"*{i}. {name}*\n"
            message += f"Category: {category}\n"
            message += f"Severity: {severity}/100\n"
            message += f"Description: {description}\n\n"
        
        await query.message.reply_text(
            message,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error sending detailed analysis: {e}")
        await query.message.reply_text(
            "❌ Sorry, an error occurred while preparing the detailed analysis."
        )

async def send_recommendations(query, results: Dict[str, Any]) -> None:
    """Send recommendations to the user."""
    try:
        recommendations = results.get('recommendations', [])
        
        message = "*💡 STRATEGIC RECOMMENDATIONS*\n\n"
        
        # Show all recommendations
        for i, recommendation in enumerate(recommendations, 1):
            message += f"{i}. {recommendation}\n\n"
        
        await query.message.reply_text(
            message,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error sending recommendations: {e}")
        await query.message.reply_text(
            "❌ Sorry, an error occurred while preparing the recommendations."
        )

async def send_pdf_report(query, results: Dict[str, Any]) -> None:
    """Send PDF report to the user."""
    try:
        report_path = results.get('report_path')
        
        if report_path and os.path.exists(report_path):
            await query.message.reply_document(
                document=open(report_path, 'rb'),
                caption="📄 UI Complexity Analysis Report"
            )
        else:
            await query.message.reply_text(
                "❌ Sorry, PDF report is not available."
            )
        
    except Exception as e:
        logger.error(f"Error sending PDF report: {e}")
        await query.message.reply_text(
            "❌ Sorry, an error occurred while sending the PDF report."
        )

async def send_heatmap(query, results: Dict[str, Any]) -> None:
    """Send heatmap to the user."""
    try:
        heatmap_path = results.get('heatmap_path')
        
        if heatmap_path and os.path.exists(heatmap_path):
            await query.message.reply_photo(
                photo=open(heatmap_path, 'rb'),
                caption="🔥 Heatmap of UI complexity issues (red areas indicate problem regions)"
            )
        else:
            await query.message.reply_text(
                "❌ Sorry, heatmap is not available."
            )
        
    except Exception as e:
        logger.error(f"Error sending heatmap: {e}")
        await query.message.reply_text(
            "❌ Sorry, an error occurred while sending the heatmap."
        )

def get_complexity_level(score: int) -> str:
    """Get the complexity level description based on score."""
    if score >= 80:
        return "Very High Complexity"
    elif score >= 60:
        return "High Complexity"
    elif score >= 40:
        return "Moderate Complexity"
    elif score >= 20:
        return "Low Complexity"
    else:
        return "Very Low Complexity"

def cleanup_user_data(user_id: int) -> None:
    """Clean up user data."""
    if user_id in user_context:
        # Remove temporary files
        screenshot_path = user_context[user_id].get('screenshot_path')
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except Exception as e:
                logger.warning(f"Error removing temporary file {screenshot_path}: {e}")
        
        # Clear user context
        user_context.pop(user_id, None)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    traceback.print_exc()
    
    # Notify user
    if update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, an error occurred. Please try again later."
        )

async def debug_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Debug handler for all message types to see what's coming in."""
    logger.info(f"DEBUG: Received update type: {update.effective_message.chat}")
    logger.info(f"DEBUG: Update content: {update}")
    logger.info(f"DEBUG: Message type: {update.message and type(update.message)}")
    
    if update.message and update.message.photo:
        logger.info(f"DEBUG: Received photo message! Photo array length: {len(update.message.photo)}")
        await process_screenshot(update, context)
    elif update.message and update.message.text:
        logger.info(f"DEBUG: Received text message: {update.message.text[:20]}...")
    else:
        logger.info("DEBUG: Received other message type")
        if update.message:
            for attr in dir(update.message):
                if not attr.startswith('_') and not callable(getattr(update.message, attr)):
                    logger.info(f"DEBUG: update.message.{attr} = {getattr(update.message, attr)}")

def main() -> None:
    """Start the bot."""
    logger.info("Starting UI Complexity Analyzer Bot")
    
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        logger.info("Created Telegram application")

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("about", about_command))
        application.add_handler(CommandHandler("test", test_analyze))  # Add test command
        
        # Add photo handler with higher priority
        application.add_handler(MessageHandler(filters.PHOTO, process_screenshot, block=False), group=1)
        logger.info("Added photo handler with priority 1")
        
        # Add debug handler with lower priority to catch all messages
        application.add_handler(MessageHandler(filters.ALL, debug_message_handler, block=False), group=2)
        logger.info("Added debug handler with priority 2")
        
        # Add text message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler), group=3)
        
        # Add callback query handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        logger.info("All handlers registered")

        # Start the Bot
        logger.info("Starting bot...")
        if 'RAILWAY_STATIC_URL' in os.environ:
            # Railway deployment with webhook
            webhook_url = os.environ.get('RAILWAY_STATIC_URL', '') + TELEGRAM_BOT_TOKEN
            port = int(os.environ.get('PORT', 5000))
            logger.info(f"Starting webhook on port {port} with URL path {TELEGRAM_BOT_TOKEN}")
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=TELEGRAM_BOT_TOKEN,
                webhook_url=webhook_url
            )
            logger.info(f"Webhook configured with URL: {webhook_url}")
        else:
            # Local deployment with polling
            logger.info("Starting polling")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        
        logger.info("Bot started")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == '__main__':
    main()
