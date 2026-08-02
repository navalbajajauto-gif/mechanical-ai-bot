"""
commands.py
All Telegram command and message handlers. Registered onto the Application
in bot.py. Each handler is wrapped with logging + error handling so one
failing command never crashes the process.
"""

import base64
import functools
import io

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import calculators
import database as db
import interview as interview_mod
import quiz as quiz_mod
from config import settings
from drawing import analyze_drawing
from image_analysis import analyze_image
from jobs import fetch_latest_jobs, format_jobs
from knowledge import TOPICS, get_today_digest, get_topic_note
from logger import get_logger
from mcq import format_mcq_for_post, generate_mcqs
from news import fetch_latest_news, summarize_news
from resume import review_resume
from utils import ask_claude, truncate

log = get_logger(__name__)


def handler(command_name: str):
    """Decorator: logs the command, records it in DB, catches errors gracefully."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            db.upsert_user(user.id, user.username, is_admin=user.id in settings.ADMIN_IDS)
            try:
                await func(update, context)
                db.log_command(user.id, command_name, success=True)
            except Exception as exc:  # noqa: BLE001
                log.exception("Command %s failed", command_name)
                db.log_command(user.id, command_name, success=False, error=str(exc))
                await update.effective_message.reply_text(
                    f"⚠️ Kuch gadbad ho gayi ({command_name}). Thodi der baad try karo."
                )
        return wrapper
    return decorator


# ---------------------------------------------------------------- basics ---

@handler("start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔧 Mechanical AI Assistant\n\n"
        "/ask <question> - anything mechanical/QA/production\n"
        "/jobs - latest mechanical jobs\n"
        "/news - latest manufacturing news\n"
        "/today - daily concept + tip\n"
        "/quiz - interactive quiz | /leaderboard\n"
        "/interview - mock interview mode\n"
        "/resume - upload resume for review\n"
        "Knowledge: /cnc /vmc /qa /gdt /production /metrology /heat /material "
        "/casting /forging /machining /tool /tolerance /runout\n"
        "Calculators: /rpm /feed /speed /oee /cycletime /tolerance\n"
        "Upload a drawing or defect photo any time - bot will analyze it."
    )


@handler("help")
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ------------------------------------------------------------------ /ask ---

ASK_SYSTEM = (
    "You are a senior mechanical/production/quality engineer helping a colleague "
    "in automotive manufacturing (two-wheeler components: crankcases, cylinder "
    "blocks, gears, clutch assemblies - HPDC casting, VMC/CNC machining). "
    "Answer in Hinglish (Hindi-English mix, Roman script), practical and direct. "
    "Use structure (headers/bullets) for longer answers."
)


@handler("ask")
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("Kuch poochna hai? Usage: /ask <your question>")
        return
    await update.message.chat.send_action("typing")
    answer = await ask_claude(question, system=ASK_SYSTEM, max_tokens=1200)
    await update.message.reply_text(truncate(answer))


# ------------------------------------------------------------ jobs/news ---

@handler("jobs")
async def jobs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    listings = await fetch_latest_jobs(limit=10)
    await update.message.reply_text(truncate(format_jobs(listings)), disable_web_page_preview=True)


@handler("news")
async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    items = await fetch_latest_news(limit=6)
    text = await summarize_news(items)
    await update.message.reply_text(truncate(text), disable_web_page_preview=True)


@handler("today")
async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    digest = await get_today_digest()
    await update.message.reply_text(truncate(digest))


# --------------------------------------------------------- knowledge base --

def make_knowledge_handler(topic: str):
    @handler(topic)
    async def _h(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.chat.send_action("typing")
        note = await get_topic_note(topic)
        await update.message.reply_text(truncate(note))
    return _h


KNOWLEDGE_HANDLERS = {topic: make_knowledge_handler(topic) for topic in TOPICS}


# ---------------------------------------------------------- calculators ---

CALC_COMMANDS = calculators.CALCULATORS


def make_calc_handler(name: str, func):
    @handler(name)
    async def _h(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            result = func(context.args)
        except calculators.CalcError as exc:
            result = f"⚠️ {exc}"
        await update.message.reply_text(result)
    return _h


CALC_HANDLERS = {name: make_calc_handler(name, fn) for name, (fn, _desc) in CALC_COMMANDS.items()}


# -------------------------------------------------------------- interview -

@handler("interview")
async def interview_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    text = await interview_mod.start_interview(update.effective_user.id)
    await update.message.reply_text(text)


# --------------------------------------------------------------- resume ---

@handler("resume")
async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Apna resume PDF/DOCX file ke roop mein bhejo (as a Telegram document), "
        "main review karke feedback dunga."
    )


async def handle_resume_document(update: Update, context: ContextTypes.DEFAULT_TYPE, extracted_text: str):
    await update.message.chat.send_action("typing")
    feedback = await review_resume(extracted_text)
    await update.message.reply_text(truncate(feedback))


# ---------------------------------------------------------------- quiz ----

@handler("quiz")
async def quiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    mcq, text = await quiz_mod.get_quiz_question(update.effective_user.id)
    if not mcq:
        await update.message.reply_text(text)
        return
    buttons = [
        InlineKeyboardButton(opt[:1], callback_data=f"quiz_answer:{i}")
        for i, opt in enumerate(mcq.options)
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([buttons]))


@handler("quiz_callback")
async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_index = int(query.data.split(":")[1])
    result = quiz_mod.answer_quiz(update.effective_user.id, chosen_index)
    if result:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(result)


@handler("leaderboard")
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(quiz_mod.format_leaderboard())


# ------------------------------------------------------ photo / document ---

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes uploaded photos: if caption mentions 'drawing', use drawing
    analysis; otherwise treat as a machine/defect problem image."""
    user = update.effective_user
    db.upsert_user(user.id, user.username, is_admin=user.id in settings.ADMIN_IDS)
    try:
        await update.message.chat.send_action("typing")
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        caption = update.message.caption or ""
        is_drawing = "drawing" in caption.lower() or "gdt" in caption.lower() or "dimension" in caption.lower()

        if is_drawing:
            result = await analyze_drawing(image_b64, "image/jpeg", caption)
        else:
            result = await analyze_image(image_b64, "image/jpeg", caption)

        await update.message.reply_text(truncate(result))
        db.log_command(user.id, "photo_analysis", success=True)
    except Exception as exc:  # noqa: BLE001
        log.exception("Photo analysis failed")
        db.log_command(user.id, "photo_analysis", success=False, error=str(exc))
        await update.message.reply_text("⚠️ Image analyze nahi ho payi. Dobara try karo.")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Free-text messages: if user has an active interview session, treat as
    an answer; otherwise nudge them toward /ask."""
    user = update.effective_user
    db.upsert_user(user.id, user.username, is_admin=user.id in settings.ADMIN_IDS)

    if interview_mod.has_active_session(user.id):
        await update.message.chat.send_action("typing")
        result = await interview_mod.submit_answer(user.id, update.message.text)
        await update.message.reply_text(result)
        return

    await update.message.reply_text(
        "Mechanical/QA/production sawaal ke liye /ask <question> use karo, ya /help dekho."
    )


# ---------------------------------------------------------------- admin ---

def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@handler("stats")
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Admin-only command.")
        return
    s = db.get_stats()
    top = "\n".join(f"  {cmd}: {count}" for cmd, count in s["top_commands"]) or "  (none yet)"
    await update.message.reply_text(
        f"📊 Bot Stats\nUsers: {s['users']}\nCommands run: {s['commands_run']}\n"
        f"Errors: {s['errors']}\nTop commands:\n{top}"
    )


@handler("broadcast")
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Admin-only command.")
        return
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    sent, failed = 0, 0
    for uid in db.get_all_user_ids():
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {message}")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"Broadcast done. Sent: {sent}, Failed: {failed}")


@handler("health")
async def health_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Admin-only command.")
        return
    await update.message.reply_text("✅ Bot is up and responding.")