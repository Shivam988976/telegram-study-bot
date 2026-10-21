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

# Configuration (Use environment variables for security in production)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8827719175:AAGiX9iflaRH0DiOWGlqUMcVemZk5jgkNNc")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6I4ko0X0hxvKOPfZeydHvQQsxNN3q5eR0yKtMpVCNMGew")

# Initialize Google GenAI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Store ongoing chat sessions
user_chats = {}

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --- Tiny Flask Web Server (Keeps the cloud host alive) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    # Render assigns a dynamic port via environment variables, default to 8080
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)


# --- Telegram Bot Logic ---
def get_or_create_chat(user_id):
    if user_id not in user_chats:
        system_instruction = (
            "You are a warm, friendly, and encouraging human study partner and mentor. "
            "Talk naturally, use an engaging tone, and be supportive."
        )
        user_chats[user_id] = ai_client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": system_instruction}
        )
    return user_chats[user_id]

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
    user_id = update.effective_user.id
    chat = get_or_create_chat(user_id)
    
    try:
        response = chat.send_message(f"Explain '{topic}' simply like a helpful study partner.")
        await send_long_message(update, response.text)
    except Exception:
        await update.message.reply_text("Ah, my brain got stuck for a second! Let's try that again.")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("What subject should we test ourselves on? E.g., `/quiz Modern History`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    user_id = update.effective_user.id
    chat = get_or_create_chat(user_id)
    
    try:
        response = chat.send_message(f"Give me 1 practice multiple-choice question on '{topic}' with options A, B, C, D, and answer at the bottom.")
        await send_long_message(update, response.text)
    except Exception:
        await update.message.reply_text("Oops, something went wrong generating the quiz.")

async def handle_general_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    chat = get_or_create_chat(user_id)

    try:
        response = chat.send_message(user_message)
        await send_long_message(update, response.text)
    except Exception:
        await update.message.reply_text("Ah, my thoughts got scattered. What were we saying?")

def main():
    # Start the Flask web server in a separate background thread
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
