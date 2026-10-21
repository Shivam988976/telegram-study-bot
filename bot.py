import logging
import os
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Configuration
TELEGRAM_TOKEN = "8827719175:AAGiX9iflaRH0DiOWGlqUMcVemZk5jgkNNc"
# PASTE YOUR HUGGINGFACE TOKEN HERE (starts with hf_...)
HF_API_KEY = "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"

# Model endpoint
HF_MODEL_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"

# Logging configuration
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


def query_huggingface(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"<|system|>\nYou are a warm, friendly, and encouraging human study partner and mentor. Talk naturally and helpfully.<|user|>\n{prompt}<|assistant|>\n",
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7,
            "return_full_text": False
        }
    }
    
    response = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "Sorry, I couldn't generate a response.")
        return str(result)
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")


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

    try:
        ai_response = query_huggingface(user_message)
        await send_long_message(update, ai_response)
    except Exception as e:
        logging.error(f"HF API Error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    app.add_error_handler(error_handler)

    print("🚀 Cloud Bot is live!")
    app.run_polling()

if __name__ == "__main__":
    main()
