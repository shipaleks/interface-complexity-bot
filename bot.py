import os
import logging
import sys
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)
import openai
from dotenv import load_dotenv
import tempfile
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH")
PORT = int(os.environ.get('PORT', 8443))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', None)
# Explicit flag to force webhook mode
WEBHOOK_MODE = os.environ.get('WEBHOOK_MODE', 'false').lower() in ('true', '1', 't')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    stream=sys.stdout  # Ensure logs go to stdout for Railway
)
logger = logging.getLogger(__name__)

# Setup OpenAI
openai.api_key = OPENAI_API_KEY

# Setup Firebase (for stats only)
if FIREBASE_CRED_PATH and os.path.exists(FIREBASE_CRED_PATH):
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    db = None

# Conversation states
WAITING_IMAGE, WAITING_DESC, WAITING_SCENARIO = range(3)

# Load the system prompt
try:
    with open("interface-complexity-prompt.md", "r") as f:
        SYSTEM_PROMPT = f.read()
    logger.info(f"Loaded system prompt, length: {len(SYSTEM_PROMPT)}")
except Exception as e:
    logger.error(f"Error loading system prompt: {e}")
    SYSTEM_PROMPT = "Analyze the interface screenshot for complexity."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command received from user {update.effective_user.id}")
    await update.message.reply_text(
        "Send me a screenshot of an interface you'd like analyzed. Optionally, you can also tell me what this interface is about and what userflow I should check."
    )
    return WAITING_IMAGE

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Help command received from user {update.effective_user.id}")
    await update.message.reply_text(
        "Send an interface screenshot. Optionally, after sending the image, you can provide a description and user scenario. I'll analyze the complexity and user flows using GPT-4.1."
    )

async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Image received from user {update.effective_user.id}")
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        logger.warning("No valid photo received")
        await update.message.reply_text("Please send a valid image.")
        return WAITING_IMAGE
    
    try:
        file = await photo.get_file()
        logger.info(f"Got file with ID: {file.file_id}, size: {photo.file_size}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            await file.download_to_drive(tf.name)
            context.user_data['image_path'] = tf.name
            logger.info(f"Image saved to: {tf.name}")
            
        await update.message.reply_text(
            "(Optional) What is this interface about? If you want to skip, type /skip."
        )
        return WAITING_DESC
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await update.message.reply_text("Error processing your image. Please try again.")
        return WAITING_IMAGE

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Description received from user {update.effective_user.id}: {update.message.text[:20]}...")
    context.user_data['description'] = update.message.text
    await update.message.reply_text(
        "(Optional) What userflow should I check? If you want to skip, type /skip."
    )
    return WAITING_SCENARIO

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Description skipped by user {update.effective_user.id}")
    context.user_data['description'] = None
    await update.message.reply_text(
        "(Optional) What userflow should I check? If you want to skip, type /skip."
    )
    return WAITING_SCENARIO

async def receive_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Scenario received from user {update.effective_user.id}: {update.message.text[:20]}...")
    context.user_data['scenario'] = update.message.text
    await analyze(update, context)
    return ConversationHandler.END

async def skip_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Scenario skipped by user {update.effective_user.id}")
    context.user_data['scenario'] = None
    await analyze(update, context)
    return ConversationHandler.END

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Starting analysis for user {update.effective_user.id}")
    
    try:
        image_path = context.user_data.get('image_path')
        if not image_path or not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            await update.message.reply_text("Error: Image file not found. Please try sending the image again.")
            return
            
        description = context.user_data.get('description')
        scenario = context.user_data.get('scenario')
        
        logger.info(f"Analysis parameters - Image: {image_path}, Description: {bool(description)}, Scenario: {bool(scenario)}")
        
        user_input = []
        if description:
            user_input.append(f"Description: {description}")
        if scenario:
            user_input.append(f"Userflow: {scenario}")
            
        prompt = SYSTEM_PROMPT
        if user_input:
            prompt += "\n\n" + "\n".join(user_input)
            
        import base64
        import json
        
        # Send a typing indicator to show the bot is processing
        await update.message.chat.send_action(action="typing")
        
        # Encode the image as base64
        with open(image_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")
            logger.info(f"Image encoded, base64 length: {len(base64_image)}")
            
        user_message = []
        user_message.append({
            "type": "text",
            "text": "Please perform a full complexity analysis of this interface."
        })
        user_message.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })
        
        logger.info("Sending request to OpenAI API...")
        
        response = openai.ChatCompletion.create(
            model="gpt-4.1",
            response_format="json",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1500,
            temperature=0.4
        )
        
        logger.info(f"OpenAI API response received, tokens: {response.usage.total_tokens}")
        
        result_json = response.choices[0].message.content
        try:
            result = json.loads(result_json)
            pretty_result = json.dumps(result, indent=2, ensure_ascii=False)
            logger.info("Successfully parsed JSON response")
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            pretty_result = result_json  # fallback if not valid JSON
            
        logger.info(f"Sending analysis result to user, length: {len(pretty_result)}")
        await update.message.reply_text(pretty_result[:4000])  # Telegram limit
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        await update.message.reply_text("Sorry, there was an error analyzing your image. Please try again later.")
    
    finally:
        # Clean up temp file
        image_path = context.user_data.get('image_path')
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                logger.info(f"Temp file removed: {image_path}")
            except Exception as e:
                logger.error(f"Error removing temp file: {e}")
        
        # Log usage to Firebase
        if db:
            try:
                user_hash = hash(update.effective_user.id)
                db.collection("usage_stats").add({
                    "user": str(user_hash),
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
                logger.info("Usage logged to Firebase")
            except Exception as e:
                logger.error(f"Error logging to Firebase: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Analysis cancelled by user {update.effective_user.id}")
    await update.message.reply_text("Analysis cancelled.")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the dispatcher."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=True)
    if update:
        try:
            await update.message.reply_text("Sorry, an error occurred. Please try again later.")
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

def main():
    # Initialize the bot with a higher timeout for API calls
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).connect_timeout(30.0).read_timeout(30.0).get_updates_read_timeout(30.0).build()
    
    # Log bot info
    logger.info(f"Bot initialized with token: {TELEGRAM_TOKEN[:5]}...{TELEGRAM_TOKEN[-5:]}")
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Add handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_IMAGE: [MessageHandler(filters.PHOTO, receive_image)],
            WAITING_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description), CommandHandler("skip", skip_description)],
            WAITING_SCENARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_scenario), CommandHandler("skip", skip_scenario)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    
    # Use webhooks if WEBHOOK_MODE is True or if WEBHOOK_URL is set
    if WEBHOOK_MODE or WEBHOOK_URL:
        webhook_url = WEBHOOK_URL or f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'example.com')}/{TELEGRAM_TOKEN}"
        logger.info(f"Starting webhook mode on port {PORT} with URL: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # Use polling for development
        logger.info("Starting polling mode")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
