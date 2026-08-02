"""
scheduler.py
Daily automatic posts:
  8 AM IST  - mechanical concept + interview question + 5 MCQs + tip
  6 PM IST  - latest jobs + latest news

Two ways this runs, both supported:
1. Persistent process (Render): APScheduler triggers these in-process on a
   cron schedule, using Asia/Kolkata timezone.
2. GitHub Actions cron (backup/redundant path): bot.py --once morning|evening
   runs a single post and exits - useful if you want the free Actions cron
   as a belt-and-braces trigger independent of the Render dyno.
"""

from telegram import Bot
from telegram.constants import ParseMode

from config import settings
from jobs import fetch_latest_jobs, format_jobs
from knowledge import get_today_digest
from logger import get_logger
from mcq import format_mcq_for_post, generate_mcqs
from news import fetch_latest_news, summarize_news

log = get_logger(__name__)


async def send_morning_post(bot: Bot) -> None:
    log.info("Building morning post")
    digest = await get_today_digest()
    mcqs = await generate_mcqs(count=5)
    mcq_text = format_mcq_for_post(mcqs)

    text = f"☀️ Good Morning! Aaj ka Mechanical Digest\n\n{digest}\n\n{mcq_text}"
    await _send_long(bot, text)
    log.info("Morning post sent")


async def send_evening_post(bot: Bot) -> None:
    log.info("Building evening post")
    jobs = await fetch_latest_jobs(limit=8)
    news_items = await fetch_latest_news(limit=6)
    news_text = await summarize_news(news_items)
    jobs_text = format_jobs(jobs)

    text = f"🌆 Evening Update\n\n{jobs_text}\n\n{news_text}"
    await _send_long(bot, text)
    log.info("Evening post sent")


async def _send_long(bot: Bot, text: str, chunk_size: int = 4000) -> None:
    for i in range(0, len(text), chunk_size):
        await bot.send_message(chat_id=settings.CHAT_ID, text=text[i : i + chunk_size])


def setup_scheduler(bot: Bot):
    """Wire APScheduler jobs for use inside a persistent (webhook) process."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        send_morning_post, CronTrigger(hour=settings.MORNING_POST_HOUR_IST, minute=0),
        args=[bot], id="morning_post", replace_existing=True,
    )
    scheduler.add_job(
        send_evening_post, CronTrigger(hour=settings.EVENING_POST_HOUR_IST, minute=0),
        args=[bot], id="evening_post", replace_existing=True,
    )
    scheduler.start()
    log.info("Scheduler started: morning=%s:00 IST, evening=%s:00 IST",
              settings.MORNING_POST_HOUR_IST, settings.EVENING_POST_HOUR_IST)
    return scheduler