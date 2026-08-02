import os
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN secret not found")

if not CHAT_ID:
    raise Exception("CHAT_ID secret not found")

bot = Bot(token=BOT_TOKEN)

message = """
🤖 Mechanical AI Assistant Bot

✅ Bot is Online

📚 Daily Mechanical Knowledge
💼 Mechanical Jobs
📝 Daily MCQs
🎯 Interview Questions

Welcome!
"""

bot.send_message(chat_id=CHAT_ID, text=message)

print("Bot started successfully")
