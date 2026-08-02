"""
image_analysis.py
Photo of a machine problem, part defect, or inspection result -> Claude vision
explains likely defect, root cause, corrective action, and prevention (8D-style).
"""

from logger import get_logger
from utils import ask_claude

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a quality/production engineer doing root-cause analysis on a shop floor. "
    "Respond in Hinglish (Hindi-English mix, Roman script), direct and practical, "
    "the way you'd talk to a colleague, not a formal report."
)

ANALYSIS_PROMPT = """Look at this image of a machine problem / part defect / inspection result and explain:

1. **Likely defect/issue** - what does this look like (e.g. porosity, cold shut, burr, tool mark, misalignment)
2. **Possible root causes** - 2-4 most likely causes for this specific defect
3. **Immediate corrective action** - what to do right now with this part/batch
4. **Preventive action** - process change to stop recurrence (poka-yoke, parameter change, etc.)
5. **Confidence note** - if the image quality/angle limits certainty, say so

Keep it concise and actionable, under 350 words."""


async def analyze_image(image_base64: str, media_type: str, caption: str = "") -> str:
    prompt = ANALYSIS_PROMPT
    if caption:
        prompt += f"\n\nUser's note/context: {caption}"

    return await ask_claude(
        prompt,
        system=SYSTEM_PROMPT,
        images=[{"media_type": media_type, "data": image_base64}],
        max_tokens=1000,
    )