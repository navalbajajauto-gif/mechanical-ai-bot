"""
news.py
Live manufacturing/automotive/Industry 4.0 news via RSS, summarized by Claude.
"""

from dataclasses import dataclass
from typing import List

import feedparser

from config import settings
from database import is_item_seen, mark_item_seen
from logger import get_logger
from utils import ask_claude, hash_text, retry_async

log = get_logger(__name__)


@dataclass
class NewsItem:
    title: str
    link: str
    summary_raw: str

    @property
    def item_hash(self) -> str:
        return hash_text(self.link or self.title)


@retry_async(max_retries=2, backoff=1.5)
async def _fetch_feed(url: str):
    parsed = feedparser.parse(url)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError(f"Feed parse failed for {url}: {parsed.bozo_exception}")
    return parsed


async def fetch_latest_news(limit: int = 8, only_new: bool = True) -> List[NewsItem]:
    items: List[NewsItem] = []

    for url in settings.NEWS_RSS_FEEDS:
        try:
            feed = await _fetch_feed(url)
        except Exception as exc:
            log.warning("Skipping news feed %s: %s", url, exc)
            continue

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            item = NewsItem(
                title=title,
                link=getattr(entry, "link", ""),
                summary_raw=getattr(entry, "summary", "")[:500],
            )
            items.append(item)

    seen_hashes = set()
    deduped: List[NewsItem] = []
    for item in items:
        h = item.item_hash
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        if only_new and is_item_seen(h):
            continue
        deduped.append(item)

    result = deduped[:limit]
    for item in result:
        mark_item_seen(item.item_hash, "news")
    return result


async def summarize_news(items: List[NewsItem]) -> str:
    if not items:
        return "Abhi koi naya manufacturing/automotive news update nahi mila."

    raw_block = "\n\n".join(f"- {it.title}: {it.summary_raw}" for it in items)
    prompt = (
        "Summarize these manufacturing/automotive/Industry-4.0 news headlines into a short "
        "Telegram-friendly Hinglish digest. One line per story, most important first, "
        "practical relevance for a factory quality/production engineer. Max 6 lines total.\n\n"
        f"{raw_block}"
    )
    summary = await ask_claude(prompt, max_tokens=500)

    lines = ["📰 Latest Manufacturing & Automotive News\n", summary, "\n🔗 Sources:"]
    for it in items[:5]:
        if it.link:
            lines.append(f"- {it.title}: {it.link}")
    return "\n".join(lines)