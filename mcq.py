"""
mcq.py
Generates mechanical engineering MCQs via Claude, returned as structured
JSON so both the daily digest post and interactive /quiz can use them.
"""

import json
import re
from dataclasses import dataclass
from typing import List

from logger import get_logger
from utils import ask_claude

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You generate mechanical engineering MCQs for automotive manufacturing professionals "
    "(CNC/VMC machining, HPDC casting, quality systems, GD&T, materials). "
    "Return ONLY valid JSON, no markdown fences, no commentary."
)

MCQ_PROMPT = """Generate {count} multiple-choice questions on mechanical engineering / manufacturing / quality topics.
Vary topics and difficulty. Return as a JSON array, each item shaped exactly like:
{{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct_index": 0, "explanation": "..."}}
correct_index is 0-based. Return ONLY the JSON array."""


@dataclass
class MCQ:
    question: str
    options: List[str]
    correct_index: int
    explanation: str


def _parse_mcqs(raw: str) -> List[MCQ]:
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        log.error("Failed to parse MCQ JSON: %s | raw=%s", exc, cleaned[:300])
        return []
    mcqs = []
    for item in data:
        try:
            mcqs.append(
                MCQ(
                    question=item["question"],
                    options=item["options"],
                    correct_index=int(item["correct_index"]),
                    explanation=item.get("explanation", ""),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return mcqs


async def generate_mcqs(count: int = 5) -> List[MCQ]:
    raw = await ask_claude(MCQ_PROMPT.format(count=count), system=SYSTEM_PROMPT, max_tokens=1500)
    return _parse_mcqs(raw)


def format_mcq_for_post(mcqs: List[MCQ]) -> str:
    if not mcqs:
        return "MCQ generate nahi ho paye is baar."
    lines = ["🧠 Today's Mechanical MCQs\n"]
    for i, m in enumerate(mcqs, 1):
        lines.append(f"{i}. {m.question}")
        lines.extend(f"   {opt}" for opt in m.options)
        lines.append("")
    lines.append("Answers neeche 👇 (spoiler - answer karne ki koshish pehle karo!)")
    for i, m in enumerate(mcqs, 1):
        correct_letter = chr(65 + m.correct_index)
        lines.append(f"{i}. {correct_letter} - {m.explanation}")
    return "\n".join(lines)