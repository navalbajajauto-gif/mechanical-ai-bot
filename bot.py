import os
import asyncio
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not found")

if not CHAT_ID:
    raise Exception("CHAT_ID not found")


async def main():
    bot = Bot(token=BOT_TOKEN)

    message = """
🤖 Mechanical AI Assistant

✅ Bot is Online

📚 Daily Mechanical Knowledge
💼 Mechanical Jobs
📝 Daily MCQs
🎯 Interview Questions

🚀 Welcome!
"""

    await bot.send_message(
        chat_id=int(CHAT_ID),
        text=message
    )

    print("✅ Message sent successfully")


asyncio.run(main())
