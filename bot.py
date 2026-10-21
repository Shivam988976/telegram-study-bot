import logging
import os
from threading import Thread
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Google GenAI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- Tiny Flask Web Server (Keeps Render alive) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)


async def send_long_message(update: Update, text: str):
    max_length = 4000
    if len(text) <= max_length:
        await update.message.reply_text(text)
    else:
        for i in range(0, len(text), max_length):
            await update.message.reply_text(text[i:i+max_length])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "there"
    welcome_text = (
        f"Hey {user_name}! 👋 So good to see you.\n\n"
        "I'm your personal study buddy, running 24/7 in the cloud! "
        "What are we studying today?"
    )
    await update.message.reply_text(welcome_text)


async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("Hmm, what topic do you want me to break down? Try `/explain Photosynthesis`!")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    prompt = f"You are a warm, friendly human study partner. Explain the topic '{topic}' simply and clearly with examples."

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        await send_long_message(update, response.text)
    except Exception as e:
        logging.error(f"Error in explain: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("What subject should we test ourselves on? E.g., `/quiz Modern History`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    prompt = f"You are a friendly study partner. Give me 1 practice multiple-choice question on '{topic}' with options A, B, C, D, and the answer at the bottom."

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        await send_long_message(update, response.text)
    except Exception as e:
        logging.error(f"Error in quiz: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    system_prompt = (
        "You are a warm, friendly, and encouraging human study partner and mentor. "
        "Talk naturally, use an engaging tone, and be supportive."
    )
    full_prompt = f"{system_prompt}\n\nUser says: {user_message}"

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        await send_long_message(update, response.text)
    except Exception as e:
        logging.error(f"Error in general message: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


def main():
    # Start the Flask web server in a background thread
    t = Thread(target=run_web)
    t.start()

    # Start Telegram Bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("explain", explain_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))

    print("🚀 Cloud Bot is live!")
    app.run_polling()

if __name__ == "__main__":
    main()
