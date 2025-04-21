import os
import logging
from telegram import Update, ReplyKeyboardMarkup, InputFile, KeyboardButton, ReplyKeyboardRemove
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
WAITING_IMAGE, WAITING_DESC, ENTERING_DESC, WAITING_SCENARIO, ENTERING_SCENARIO = range(5)

# Load the system prompt
with open("interface-complexity-prompt.md", "r") as f:
    SYSTEM_PROMPT = f.read()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для анализа UI/UX интерфейсов. 🚀\n\n"
        "Отправь мне скриншот интерфейса для анализа.\n"
        "После этого у тебя будет возможность добавить описание и сценарии использования "
        "или сразу перейти к анализу."
    )
    return WAITING_IMAGE

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Как использовать бота:\n\n"
        "1. Отправьте скриншот интерфейса 📱\n"
        "2. Выберите, хотите ли вы добавить описание того, что изображено на скриншоте (опционально) 📝\n"
        "3. Выберите, хотите ли вы добавить основные пользовательские сценарии (опционально) 🔄\n"
        "4. Дождитесь результатов анализа ⏳\n\n"
        "Я проведу когнитивный анализ интерфейса и предоставлю:\n"
        "- Стратегическую интерпретацию проблем 🧠\n"
        "- Рекомендации по улучшению 💡\n"
        "- PDF-отчет с детальным анализом 📊\n"
        "- Тепловую карту проблемных зон 🔥\n\n"
        "Команды:\n"
        "/start - Начать взаимодействие\n"
        "/cancel - Отменить текущий анализ\n"
        "/help - Показать эту справку"
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
    
    # Create keyboard with options
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить")],
            [KeyboardButton(text="Ввести описание")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "Что изображено на скриншоте? Это поможет сделать анализ более точным.",
        reply_markup=keyboard
    )
    return WAITING_DESC

async def handle_description_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "Пропустить":
        context.user_data['description'] = None
        return await offer_scenario_options(update, context)
    elif text == "Ввести описание":
        await update.message.reply_text(
            "Пожалуйста, опишите, что изображено на скриншоте:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ENTERING_DESC
    else:
        context.user_data['description'] = text
        return await offer_scenario_options(update, context)

async def entering_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    return await offer_scenario_options(update, context)

async def offer_scenario_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить")],
            [KeyboardButton(text="Ввести сценарии")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        "Какие основные пользовательские сценарии (user flows) связаны с этим интерфейсом? Это поможет сделать анализ более релевантным.",
        reply_markup=keyboard
    )
    return WAITING_SCENARIO

async def handle_scenario_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "Пропустить":
        context.user_data['scenario'] = None
        return await start_analysis(update, context)
    elif text == "Ввести сценарии":
        await update.message.reply_text(
            "Пожалуйста, опишите основные сценарии использования этого интерфейса:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ENTERING_SCENARIO
    else:
        context.user_data['scenario'] = text
        return await start_analysis(update, context)

async def entering_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['scenario'] = update.message.text
    return await start_analysis(update, context)

async def start_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Спасибо! Начинаю анализ интерфейса. Это может занять несколько минут...",
        reply_markup=ReplyKeyboardRemove()
    )
    return await analyze(update, context)

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
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Analysis cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_IMAGE: [MessageHandler(filters.PHOTO, receive_image)],
            WAITING_DESC: [MessageHandler(filters.TEXT, handle_description_choice)],
            ENTERING_DESC: [MessageHandler(filters.TEXT, entering_description)],
            WAITING_SCENARIO: [MessageHandler(filters.TEXT, handle_scenario_choice)],
            ENTERING_SCENARIO: [MessageHandler(filters.TEXT, entering_scenario)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()

if __name__ == "__main__":
    main()
