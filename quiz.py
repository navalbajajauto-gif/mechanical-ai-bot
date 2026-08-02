"""
quiz.py
Interactive /quiz mode: one MCQ at a time via inline keyboard, score tracked
in DB, /leaderboard shows top scorers.
"""

from typing import Dict, Optional

from database import get_leaderboard, update_quiz_score
from logger import get_logger
from mcq import MCQ, generate_mcqs

log = get_logger(__name__)

# In-memory active question per user (short-lived, fine to lose on restart -
# worst case user gets a fresh question next time).
_active_quiz: Dict[int, MCQ] = {}


async def get_quiz_question(user_id: int) -> tuple:
    mcqs = await generate_mcqs(count=1)
    if not mcqs:
        return None, "Quiz question generate nahi ho payi, thodi der baad try karo."
    mcq = mcqs[0]
    _active_quiz[user_id] = mcq

    text = f"🧠 Quiz Time!\n\n{mcq.question}\n\n" + "\n".join(mcq.options)
    return mcq, text


def answer_quiz(user_id: int, chosen_index: int) -> Optional[str]:
    mcq = _active_quiz.pop(user_id, None)
    if not mcq:
        return None

    correct = chosen_index == mcq.correct_index
    stats = update_quiz_score(user_id, correct)

    if correct:
        result = "✅ Correct!"
    else:
        correct_letter = chr(65 + mcq.correct_index)
        result = f"❌ Wrong. Sahi jawab: {correct_letter}"

    return (
        f"{result}\n{mcq.explanation}\n\n"
        f"Score: {stats['score']} | Attempts: {stats['attempts']}\n"
        f"/quiz next question ke liye."
    )


def format_leaderboard() -> str:
    rows = get_leaderboard(limit=10)
    if not rows:
        return "Abhi leaderboard khaali hai. /quiz khelo aur pehla banoo!"
    lines = ["🏆 Quiz Leaderboard\n"]
    for i, r in enumerate(rows, 1):
        name = r["username"] or "Anonymous"
        lines.append(f"{i}. {name} - {r['score']} pts ({r['attempts']} attempts)")
    return "\n".join(lines)