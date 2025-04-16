#!/usr/bin/env python3
import os
import json
import logging
import asyncio
import tempfile
from typing import Dict, Any, List, Optional
import traceback
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

from analyze_ui import UIAnalyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is not set in the environment variables")
    raise ValueError("TELEGRAM_BOT_TOKEN is required")

# Create output directory for analysis results
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create analyzer
analyzer = UIAnalyzer(output_dir=OUTPUT_DIR)

# User context storage
user_context: Dict[int, Dict[str, Any]] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
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

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send information about UI complexity analysis."""
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

async def process_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a screenshot sent by the user."""
    user_id = update.effective_user.id
    
    # Send processing message
    processing_message = await update.message.reply_text(
        "🔍 Processing your screenshot. This will take about 1-2 minutes..."
    )
    
    # Get the photo with the highest resolution
    photo = update.message.photo[-1]
    
    try:
        # Create a temporary directory for this user
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the photo
            photo_file = await context.bot.get_file(photo.file_id)
            screenshot_path = os.path.join(temp_dir, f"screenshot_{photo.file_id}.jpg")
            await photo_file.download_to_drive(screenshot_path)
            
            # Store the screenshot path in user context
            if user_id not in user_context:
                user_context[user_id] = {}
            user_context[user_id]['screenshot_path'] = screenshot_path
            
            # Check if we need more context
            # For now, let's proceed directly to analysis
            await processing_message.edit_text(
                "🔎 Analyzing your interface for complexity issues and usability problems..."
            )
            
            # Analyze the screenshot
            return await perform_analysis(update, context, screenshot_path, processing_message)
            
    except Exception as e:
        logger.error(f"Error processing screenshot: {e}")
        traceback.print_exc()
        await processing_message.edit_text(
            "❌ Sorry, an error occurred while processing your screenshot. Please try again later."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "show_details":
        # Show more detailed analysis
        if user_id in user_context and 'analysis_results' in user_context[user_id]:
            results = user_context[user_id]['analysis_results']
            await send_detailed_analysis(query, results)
    
    elif data == "show_recommendations":
        # Show recommendations
        if user_id in user_context and 'analysis_results' in user_context[user_id]:
            results = user_context[user_id]['analysis_results']
            await send_recommendations(query, results)
    
    elif data == "send_report":
        # Send PDF report
        if user_id in user_context and 'analysis_results' in user_context[user_id]:
            results = user_context[user_id]['analysis_results']
            await send_pdf_report(query, results)
    
    elif data == "send_heatmap":
        # Send heatmap
        if user_id in user_context and 'analysis_results' in user_context[user_id]:
            results = user_context[user_id]['analysis_results']
            await send_heatmap(query, results)

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages."""
    await update.message.reply_text(
        "Please send me a screenshot of a user interface to analyze. "
        "Text analysis is not supported at this time."
    )

async def perform_analysis(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    screenshot_path: str, 
    processing_message: Any
) -> None:
    """Perform the UI analysis and send results."""
    try:
        user_id = update.effective_user.id
        
        # Analyze screenshot
        results = await analyzer.analyze_screenshot(screenshot_path)
        
        # Store results in user context
        if user_id not in user_context:
            user_context[user_id] = {}
        user_context[user_id]['analysis_results'] = results
        
        # Update processing message
        await processing_message.edit_text("✅ Analysis complete! Preparing your results...")
        
        # Send initial results
        await send_initial_results(update, context, results)
        
    except Exception as e:
        logger.error(f"Error performing analysis: {e}")
        traceback.print_exc()
        await processing_message.edit_text(
            "❌ Sorry, an error occurred while analyzing your screenshot. Please try again later."
        )

async def send_initial_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: Dict[str, Any]) -> None:
    """Send initial analysis results to the user."""
    try:
        # Extract data
        overall_score = results.get('overall_score', 0)
        categories = results.get('categories', {})
        top_issues = results.get('top_issues', [])
        
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
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # If we have a heatmap, send it
        heatmap_path = results.get('heatmap_path')
        if heatmap_path and os.path.exists(heatmap_path):
            await update.message.reply_photo(
                photo=open(heatmap_path, 'rb'),
                caption="🔥 Heatmap of UI complexity issues (red areas indicate problem regions)"
            )
        
    except Exception as e:
        logger.error(f"Error sending results: {e}")
        traceback.print_exc()
        await update.message.reply_text(
            "❌ Sorry, an error occurred while preparing your results. The analysis was completed successfully, "
            "but we couldn't format the results properly."
        )

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

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Add photo handler
    application.add_handler(MessageHandler(filters.PHOTO, process_screenshot))
    
    # Add text message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    if 'RAILWAY_STATIC_URL' in os.environ:
        # Railway deployment with webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get('PORT', 5000)),
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=os.environ.get('RAILWAY_STATIC_URL', '') + TELEGRAM_BOT_TOKEN
        )
    else:
        # Local deployment with polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Bot started")

if __name__ == '__main__':
    main()
