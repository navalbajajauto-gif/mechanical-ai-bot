"""
interview.py
Interactive mechanical engineering interview mode.
Flow: /interview -> Claude asks a question -> user answers -> Claude evaluates
+ explains mistakes + asks next question. State persisted per-user in DB so it
survives across webhook requests (each request may hit a fresh process).
"""

import json

from database import clear_interview_session, get_interview_session, save_interview_session
from logger import get_logger
from utils import ask_claude

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are conducting a mock mechanical engineering interview for a production/quality "
    "engineering role in automotive manufacturing. Ask one focused question at a time. "
    "Mix topics: manufacturing processes, GD&T, quality systems (FMEA, 8D), machining, "
    "materials. Respond in Hinglish (Hindi-English, Roman script). Be encouraging but honest."
)

QUESTION_PROMPT = """Ask ONE mechanical engineering interview question suitable for question #{qnum} "
of a mock interview (vary difficulty and topic from typical earlier questions).
Return ONLY the question text, nothing else - no preamble, no numbering."""

EVAL_PROMPT = """The interview question was:
"{question}"

The candidate answered:
"{answer}"

Evaluate the answer:
1. Correct/Incorrect/Partially correct
2. What was good
3. What was missing or wrong (explain the mistake clearly)
4. The ideal answer in 2-3 lines

Keep it under 200 words, Hinglish, direct."""


async def start_interview(user_id: int, topic: str = "general") -> str:
    question = await ask_claude(QUESTION_PROMPT.format(qnum=1), system=SYSTEM_PROMPT, max_tokens=200)
    save_interview_session(user_id, topic, 1, question, 0)
    return f"🎤 Interview Mode Start!\n\nQuestion 1:\n{question}\n\n(Reply with your answer)"


async def submit_answer(user_id: int, answer: str) -> str:
    session = get_interview_session(user_id)
    if not session:
        return "Koi active interview session nahi hai. /interview bhejo start karne ke liye."

    question = session["current_question"]
    qnum = session["question_num"]

    evaluation = await ask_claude(
        EVAL_PROMPT.format(question=question, answer=answer),
        system=SYSTEM_PROMPT,
        max_tokens=500,
    )

    is_correct = evaluation.lower().startswith("correct") or "1. correct" in evaluation.lower()[:30]
    new_score = session["score"] + (1 if is_correct else 0)

    next_qnum = qnum + 1
    if next_qnum >