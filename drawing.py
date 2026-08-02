"""
drawing.py
Engineering drawing analysis. User uploads a drawing image; Claude vision
explains GD&T, dimensions, tolerances, datums, inspection points, and the
likely manufacturing process.
"""

from logger import get_logger
from utils import ask_claude

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a senior manufacturing/quality engineer reading an engineering drawing "
    "(mechanical component, likely automotive - crankcase, cylinder block, gear, shaft, "
    "or similar). Explain it the way you'd brief a shop-floor engineer, in Hinglish "
    "(Hindi-English mix, Roman script). Be practical, not academic."
)

ANALYSIS_PROMPT = """Analyze this engineering drawing and explain, with clear section headers:

1. **Part identification** - what kind of part does this look like
2. **Key dimensions** - critical dimensions visible, with tolerances
3. **GD&T callouts** - any feature control frames, datums (A, B, C etc.), what they control
4. **Fits & tolerances** - any fit classes (e.g. H8/g7), surface finish (Ra) notes
5. **Critical-to-quality dimensions** - which dimensions likely need 100% inspection
6. **Suggested inspection method** - CMM, gauge, go/no-go, etc. for the critical features
7. **Likely manufacturing process** - casting, machining, forging etc. based on the drawing

If any section isn't visible/legible in the image, say so briefly rather than guessing.
Keep the whole response under 400 words."""


async def analyze_drawing(image_base64: str, media_type: str, caption: str = "") -> str:
    prompt = ANALYSIS_PROMPT
    if caption:
        prompt += f"\n\nUser's note: {caption}"

    return await ask_claude(
        prompt,
        system=SYSTEM_PROMPT,
        images=[{"media_type": media_type, "data": image_base64}],
        max_tokens=1200,
    )