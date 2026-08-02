"""
resume.py
Resume review for mechanical/production/quality engineering roles.
Accepts extracted resume text (PDF/doc text extraction happens in bot.py's
document handler) and returns structured improvement feedback.
"""

from logger import get_logger
from utils import ask_claude, truncate

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a career coach specializing in mechanical/production/quality engineering "
    "roles in Indian automotive manufacturing (companies like Bajaj Auto, Tata Motors, "
    "Bosch, etc.). Respond in Hinglish (Hindi-English mix, Roman script), direct and "
    "encouraging but honest about weaknesses."
)

REVIEW_PROMPT = """Review this resume for a mechanical/production/quality engineering role. Give:

1. **Overall impression** - 1-2 lines
2. **Strengths** - what's working well
3. **Gaps to fix** - missing keywords, weak bullet points, formatting issues
4. **Rewrite suggestions** - pick 2-3 weak bullet points and show improved versions
5. **ATS/keyword check** - important mechanical/QA keywords missing (GD&T, PFMEA, CNC, etc. as relevant)

Resume text:
---
{resume_text}
---

Keep the response under 500 words, use clear section headers."""


async def review_resume(resume_text: str) -> str:
    resume_text = truncate(resume_text, 6000)
    prompt = REVIEW_PROMPT.format(resume_text=resume_text)
    return await