import os
import logging
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

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
with open("interface-complexity-prompt.md", "r") as f:
    SYSTEM_PROMPT = f.read()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a screenshot of an interface you'd like analyzed. Optionally, you can also tell me what this interface is about and what userflow I should check."
    )
    return WAITING_IMAGE

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send an interface screenshot. Optionally, after sending the image, you can provide a description and user scenario. I'll analyze the complexity and user flows using GPT-4.1."
    )

async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        await update.message.reply_text("Please send a valid image.")
        return WAITING_IMAGE
    file = await photo.get_file()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
        await file.download_to_drive(tf.name)
        context.user_data['image_path'] = tf.name
    await update.message.reply_text(
        "(Optional) What is this interface about? If you want to skip, type /skip."
    )
    return WAITING_DESC

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text(
        "(Optional) What userflow should I check? If you want to skip, type /skip."
    )
    return WAITING_SCENARIO

async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = None
    await update.message.reply_text(
        "(Optional) What userflow should I check? If you want to skip, type /skip."
    )
    return WAITING_SCENARIO

async def receive_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['scenario'] = update.message.text
    await analyze(update, context)
    return ConversationHandler.END

async def skip_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['scenario'] = None
    await analyze(update, context)
    return ConversationHandler.END

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    image_path = context.user_data.get('image_path')
    description = context.user_data.get('description')
    scenario = context.user_data.get('scenario')
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
    # Encode the image as base64
    with open(image_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode("utf-8")
    user_message = []
    user_message.append({
        "type": "text",
        "text": "Please perform a full complexity analysis of this interface."  # You can make this more dynamic if needed
    })
    user_message.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
        }
    })
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
    result_json = response.choices[0].message.content
    try:
        result = json.loads(result_json)
        pretty_result = json.dumps(result, indent=2, ensure_ascii=False)
    except Exception:
        pretty_result = result_json  # fallback if not valid JSON
    await update.message.reply_text(pretty_result[:4000])  # Telegram limit
    # Clean up temp file
    try:
        os.remove(image_path)
    except Exception:
        pass
    # Log usage to Firebase
    if db:
        user_hash = hash(update.effective_user.id)
        db.collection("usage_stats").add({
            "user": str(user_hash),
            "timestamp": firestore.SERVER_TIMESTAMP
        })

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analysis cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
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
    app.run_polling()

if __name__ == "__main__":
    main()
