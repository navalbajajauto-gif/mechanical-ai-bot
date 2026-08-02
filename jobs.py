"""
jobs.py
Live mechanical/production/QA job aggregation via public RSS feeds.
NOTE: LinkedIn and Naukri do not offer scraping-friendly public feeds and
scraping them directly violates their Terms of Service. This module pulls
from RSS-exposed sources (Indeed regional RSS, and any feed you add in
config.JOB_RSS_FEEDS) and is built so you can add more feeds - including
official job-board APIs if you get API access later - without touching
the calling code.
"""

import time
from dataclasses import dataclass
from typing import List

import feedparser

from config import settings
from database import is_item_seen, mark_item_seen
from logger import get_logger
from utils import hash_text, retry_async

log = get_logger(__name__)

MECHANICAL_KEYWORDS = [
    "mechanical", "production", "quality", "manufacturing", "cnc", "vmc",
    "machining", "casting", "hpdc", "die cast", "gear", "automotive",
    "process engineer", "maintenance engineer", "tool room", "metrology",
]


@dataclass
class JobListing:
    title: str
    company: str
    link: str
    published: str

    @property
    def item_hash(self) -> str:
        return hash_text(self.link or f"{self.title}{self.company}")


def _is_mechanical_related(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in MECHANICAL_KEYWORDS)


@retry_async(max_retries=2, backoff=1.5)
async def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    # feedparser does blocking I/O; fine for our low request volume,
    # but wrap in retry since feeds occasionally 5xx.
    parsed = feedparser.parse(url)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError(f"Feed parse failed for {url}: {parsed.bozo_exception}")
    return parsed


async def fetch_latest_jobs(limit: int = 10, only_new: bool = True) -> List[JobListing]:
    all_jobs: List[JobListing] = []

    for url in settings.JOB_RSS_FEEDS:
        try:
            feed = await _fetch_feed(url)
        except Exception as exc:
            log.warning("Skipping job feed %s: %s", url, exc)
            continue

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            if not title or not _is_mechanical_related(title):
                continue
            job = JobListing(
                title=title,
                company=getattr(entry, "author", "") or getattr(entry, "source", {}).get("title", "Unknown"),
                link=getattr(entry, "link", ""),
                published=getattr(entry, "published", ""),
            )
            all_jobs.append(job)

    # Dedup by link/title hash.
    seen_hashes = set()
    deduped: List[JobListing] = []
    for job in all_jobs:
        h = job.item_hash
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        if only_new and is_item_seen(h):
            continue
        deduped.append(job)

    # Sort newest first (best-effort on published string; RSS order is usually already newest-first).
    deduped.sort(key=lambda j: j.published, reverse=True)

    result = deduped[:limit]
    for job in result:
        mark_item_seen(job.item_hash, "job")

    return result


def format_jobs(jobs: List[JobListing]) -> str:
    if not jobs:
        return (
            "Abhi koi naya mechanical job listing nahi mili sources mein. "
            "Thodi der baad /jobs try karo, ya naye feeds config.py mein add karo."
        )
    lines = ["💼 Latest Mechanical/Production/QA Jobs\n"]
    for i, job in enumerate(jobs, 1):
        lines.append(f"{i}. {job.title}\n   🏢 {job.company}\n   🔗 {job.link}\n")
    return "\n".join(lines)