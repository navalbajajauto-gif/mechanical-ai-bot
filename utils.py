"""
utils.py
Shared helpers: retry/backoff decorator, a thin Anthropic (Claude) client
wrapper used by every AI-powered feature, and small text utilities.
"""

import asyncio
import functools
import hashlib
from typing import Any, Callable, Optional

import anthropic

from config import settings
from logger import get_logger

log = get_logger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None


def get_claude_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def retry_async(max_retries: int = None, backoff: float = None):
    """Decorator: retry an async function with exponential backoff on failure."""
    max_retries = max_retries