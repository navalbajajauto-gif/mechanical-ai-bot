"""
config.py
Central configuration for Mechanical AI Telegram Bot.
Everything that changes between environments lives here and is pulled from
environment variables (set as GitHub Secrets / Render Environment Variables).
No secrets or hardcoded values should live anywhere else in the codebase.
"""

import os
from dataclasses import dataclass, field
from typing import List


def _get_env(name: str, default: str = "", required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in GitHub Secrets (for Actions) or Render Environment (for the web service)."
        )
    return value


def _get_env_list(name: str, default: str = "") -> List[str]:
    raw = _get_env(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    # --- Telegram ---
    BOT_TOKEN: str = field(default_factory=lambda: _get_env("BOT_TOKEN", required=True))
    CHAT_ID: str = field(default_factory=lambda: _get_env("CHAT_ID", required=True))
    ADMIN_IDS: List[int] = field(
        default_factory=lambda: [int(x) for x in _get_env_list("ADMIN_IDS")]
    )

    # --- Anthropic (Claude) ---
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: _get_env("ANTHROPIC_API_KEY", required=True))
    CLAUDE_MODEL: str = field(default_factory=lambda: _get_env("CLAUDE_MODEL", "claude-sonnet-4-6"))
    CLAUDE_MAX_TOKENS: int = 1500

    # --- Hosting / webhook (Render) ---
    RUN_MODE: str = field(default_factory=lambda: _get_env("RUN_MODE", "webhook"))  # "webhook" | "polling" | "once"
    WEBHOOK_BASE_URL: str = field(default_factory=lambda: _get_env("WEBHOOK_BASE_URL"))  # e.g. https://your-app.onrender.com
    WEBHOOK_SECRET: str = field(default_factory=lambda: _get_env("WEBHOOK_SECRET", "mechanical-ai-bot-hook"))
    PORT: int = field(default_factory=lambda: int(_get_env("PORT", "10000")))

    # --- Scheduling (IST) ---
    MORNING_POST_HOUR_IST: int = 8
    EVENING_POST_HOUR_IST: int = 18

    # --- Job sources (RSS / public feeds, no scraping of ToS-restricted sites) ---
    JOB_SEARCH_KEYWORDS: List[str] = field(
        default_factory=lambda: [
            "mechanical engineer", "production engineer", "quality engineer",
            "CNC", "VMC", "manufacturing engineer", "HPDC", "die casting",
        ]
    )
    JOB_RSS_FEEDS: List[str] = field(
        default_factory=lambda: [
            "https://www.indeed.co.in/rss?q=mechanical+engineer&l=India",
            "https://www.indeed.co.in/rss?q=production+engineer&l=India",
            "https://www.indeed.co.in/rss?q=quality+engineer+manufacturing&l=India",
        ]
    )

    # --- News sources (RSS, free & reliable) ---
    NEWS_RSS_FEEDS: List[str] = field(
        default_factory=lambda: [
            "https://www.autocarpro.in/rss/news",
            "https://www.thehindubusinessline.com/economy/logistics/feeder/default.rss",
            "https://www.manufacturingtomorrow.com/rss/news.xml",
            "https://www.industryweek.com/rss.xml",
        ]
    )

    # --- Paths ---
    DATA_DIR: str = "data"
    LOG_DIR: str = "logs"
    CACHE_DIR: str = "cache"
    DB_PATH: str = os.path.join("data", "bot.db")
    LOG_FILE: str = os.path.join("logs", "bot.log")

    # --- Rate limiting / retry ---
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 2.0
    REQUEST_TIMEOUT_SECONDS: int = 20


settings = Settings()