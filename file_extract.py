"""
file_extract.py
Extracts plain text from uploaded PDF/DOCX Telegram documents (used by the
/resume flow, and reusable for any future document-based feature).
"""

import io

from telegram import Bot, Document

from logger import get_logger

log = get_logger(__name__)


async def extract_text_from_telegram_document(document: Document, bot: Bot) -> str:
    tg_file = await document.get_file()
    buf = io.BytesIO()
    await tg_file.download_to_memory(buf)
    buf.seek(0)

    filename = (document.file_name or "").lower()

    if filename.endswith(".pdf"):
        return _extract_pdf(buf)
    if filename.endswith(".docx"):
        return _extract_docx(buf)

    raise ValueError(f"Unsupported file type: {filename}")


def _extract_pdf(buf: io.BytesIO) -> str:
    import pypdf

    reader = pypdf.PdfReader(buf)
    text_parts = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError("No extractable text found (scanned/image PDF not supported).")
    return text


def _extract_docx(buf: io.BytesIO) -> str:
    import docx

    doc = docx.Document(buf)
    text = "\n".join(p.text for p in doc.paragraphs).strip()
    if not text:
        raise ValueError("No extractable text found in DOCX.")
    return text