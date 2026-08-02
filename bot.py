"""
bot.py
Main entrypoint.

Modes (set via RUN_MODE env var or --mode CLI arg):
  webhook  - persistent process, serves Telegram webhook + runs APScheduler
             for the 8AM/6PM IST posts. Use this on Render.
  polling  - persistent process using long-polling (simpler for local dev,
             no public URL needed).
  once     - runs a single scheduled post (morning|evening) and exits.
             Use this from GitHub Actions cron as a redundant/backup trigger
             that doesn't depend on the Render dyno being awake.
"""

import argparse
import asyncio
import sys

from telegram import Bot, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import commands
from config import settings
from database import init_db
from logger import get_logger
from scheduler import send_evening_post, send_morning_post, setup_scheduler

log = get_logger(__name__)


def build_application() -> Application:
    app = Application.builder().token(settings.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", commands.start))
    app.add_handler(CommandHandler("help", commands.help_cmd))
    app.add_handler(CommandHandler("ask", commands.ask))
    app.add_handler(CommandHandler("jobs", commands.jobs_cmd))
    app.add_handler(CommandHandler("news", commands.news_cmd))
    app.add_handler(CommandHandler("today", commands.today_cmd))
    app.add_handler(CommandHandler("interview", commands.interview_cmd))
    app.add_handler(CommandHandler("resume", commands.resume_cmd))
    app.add_handler(CommandHandler("quiz", commands.quiz_cmd))
    app.add_handler(CommandHandler("leaderboard", commands.leaderboard_cmd))
    app.add_handler(CommandHandler("stats", commands.stats_cmd))
    app.add_handler(CommandHandler("broadcast", commands.broadcast_cmd))
    app.add_handler(CommandHandler("health", commands.health_cmd))

    for topic, h in commands.KNOWLEDGE_HANDLERS.items():
        app.add_handler(CommandHandler(topic, h))

    for name, h in commands.CALC_HANDLERS.items():
        app.add_handler(CommandHandler(name, h))

    app.add_handler(CallbackQueryHandler(commands.quiz_callback, pattern=r"^quiz_answer:"))

    app.add_handler(MessageHandler(filters.PHOTO, commands.handle_photo))
    app.add_handler(
        MessageHandler(
            filters.Document.PDF | filters.Document.FileExtension("docx"),
            _document_router,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, commands.handle_text_message))

    return app


async def _document_router(update, context):
    """Routes uploaded PDF/DOCX to resume review (only entry point that needs
    a document upload right now; extend here for other document-based features)."""
    from file_extract import extract_text_from_telegram_document

    await update.message.chat.send_action("typing")
    try:
        text = await extract_text_from_telegram_document(update.message.document, context.bot)
    except Exception:
        log.exception("Document extraction failed")
        await update.message.reply_text("⚠️ File padh nahi paya. PDF ya DOCX bhejo, clear scan ho.")
        return
    await commands.handle_resume_document(update, context, text)


async def run_webhook() -> None:
    init_db()
    app = build_application()
    setup_scheduler(app.bot)

    webhook_path = f"/webhook/{settings.WEBHOOK_SECRET}"
    webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}{webhook_path}"

    log.info("Starting webhook server on port %s, url=%s", settings.PORT, webhook_url)
    await app.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)

    await app.initialize()
    await app.start()
    from telegram.ext import Updater  # noqa: F401 - ensures webhook server deps loaded

    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=settings.PORT,
        url_path=webhook_path,
        webhook_url=webhook_url,
    )
    log.info("Webhook server running")

    # Keep the process alive.
    stop_event = asyncio.Event()
    await stop_event.wait()


async def run_polling() -> None:
    init_db()
    app = build_application()
    setup_scheduler(app.bot)
    log.info("Starting long-polling")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    stop_event = asyncio.Event()
    await stop_event.wait()


async def run_once(which: str) -> None:
    init_db()
    bot = Bot(token=settings.BOT_TOKEN)
    if which == "morning":
        await send_morning_post(bot)
    elif which == "evening":
        await send_evening_post(bot)
    else:
        raise ValueError(f"Unknown one-off job: {which}")


def main():
    parser = argparse.ArgumentParser(description="Mechanical AI Telegram Bot")
    parser.add_argument("--mode", choices=["webhook", "polling", "once"], default=settings.RUN_MODE)
    parser.add_argument("--which", choices=["morning", "evening"], help="Required when --mode once")
    args = parser.parse_args()

    if args.mode == "webhook":
        asyncio.run(run_webhook())
    elif args.mode == "polling":
        asyncio.run(run_polling())
    elif args.mode == "once":
        if not args.which:
            print("--which morning|evening is required for --mode once", file=sys.stderr)
            sys.exit(1)
        asyncio.run(run_once(args.which))


if __name__ == "__main__":
    main()