import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


HELP_TEXT = """
🤖 Mechanical AI Assistant

Available Commands

/help - Show all commands
/today - Today's Mechanical Topic
/mcq - 5 Mechanical MCQs
/qa - Quality Knowledge
/cnc - CNC & VMC
/gdt - GD&T
/production - Production Tips
/interview - Interview Question
/jobs - Mechanical Jobs

Version 1.0
"""


TODAY_TEXT = """
📚 Today's Topic

Bearing

Bearing supports rotating shafts and reduces friction.

Types

• Ball Bearing
• Roller Bearing
• Needle Bearing
• Taper Roller Bearing
• Thrust Bearing

Interview Question

Q. Why is preload given in bearings?

Answer:
To reduce play, improve accuracy and increase stiffness.
"""


MCQ_TEXT = """
📝 Mechanical MCQs

1. SI Unit of Force?
A) Joule
B) Newton ✅
C) Pascal
D) Watt

2. Least Count of Vernier?
A) 0.02 mm ✅
B) 0.2 mm
C) 0.5 mm
D) 1 mm

3. HRC is used for?
A) Pressure
B) Hardness ✅
C) Length
D) Weight

4. CNC stands for?
Computer Numerical Control ✅

5. GD&T Full Form?
Geometric Dimensioning & Tolerancing ✅
"""


QA_TEXT = """
🏭 QA Knowledge

Quality = Product meets customer requirement.

7 QC Tools

• Check Sheet
• Histogram
• Pareto
• Fishbone
• Scatter Diagram
• Control Chart
• Flow Chart
"""


CNC_TEXT = """
⚙ CNC/VMC

Offset Types

G54
G55
G56
Tool Offset
Wear Offset

Daily Checks

✔ Air Pressure
✔ Lubrication
✔ Coolant
✔ Hydraulic Oil
✔ Alarm History
"""


GDT_TEXT = """
📐 GD&T Symbols

Flatness
Straightness
Parallelism
Perpendicularity
Position
Runout
Profile

Always read datum first.
"""


PRODUCTION_TEXT = """
🏭 Production Tips

• Eliminate Waste
• Reduce Cycle Time
• Follow SOP
• Improve OEE
• Follow Poka Yoke
• Root Cause Analysis
"""


INTERVIEW_TEXT = """
🎯 Interview Question

What is Runout?

Runout controls the variation of a rotating surface while rotating around its datum axis.

Examples

• Face Runout
• Circular Runout
• Total Runout
"""


JOBS_TEXT = """
💼 Jobs

Live Jobs Module
Coming in next update...
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Mechanical AI Assistant\n\nType /help"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TODAY_TEXT)


async def mcq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MCQ_TEXT)


async def qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(QA_TEXT)


async def cnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CNC_TEXT)


async def gdt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GDT_TEXT)


async def production(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PRODUCTION_TEXT)


async def interview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(INTERVIEW_TEXT)


async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(JOBS_TEXT)


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("mcq", mcq))
    app.add_handler(CommandHandler("qa", qa))
    app.add_handler(CommandHandler("cnc", cnc))
    app.add_handler(CommandHandler("gdt", gdt))
    app.add_handler(CommandHandler("production", production))
    app.add_handler(CommandHandler("interview", interview))
    app.add_handler(CommandHandler("jobs", jobs))

    print("Mechanical AI Bot Started")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
