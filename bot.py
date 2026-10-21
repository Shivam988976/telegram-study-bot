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

# Replace AIzaSy... with your ACTUAL key from Google AI Studio
TELEGRAM_TOKEN = "8827719175:AAGiX9iflaRH0DiOWGlqUMcVemZk5jgkNNc"
GEMINI_API_KEY = "AQ.Ab8RN6LK4hrPX0fqZvLi3DfUCxIMAC_6CjmslFxtKspwsq9lEQ"  # Must start with AIzaSy...

# Initialize Google GenAI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- Tiny Flask Web Server (Keeps Render alive 24/7) ---
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
        logging.error(f"Gemini API Error: {e}")
        await update.message.reply_text(f"⚠️ Error from AI service: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs errors caused by Updates."""
    logging.error("Exception while handling an update:", exc_info=context.error)


def main():
    # Start Flask Web Server
    t = Thread(target=run_web)
    t.start()

    # Build Telegram Bot Application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message))

    # Add explicit error handler to resolve 'No error handlers are registered'
    app.add_error_handler(error_handler)

    print("🚀 Cloud Bot is live!")
    app.run_polling()

if __name__ == "__main__":
    main()
