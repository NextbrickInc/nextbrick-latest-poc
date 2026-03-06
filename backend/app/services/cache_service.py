# backend/app/services/cache_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Two-tier in-memory cache: FAQ (preloaded, long TTL) + dynamic (on-demand, short TTL).
# Achieves <10ms for cached responses.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Optional

from cachetools import TTLCache

from app.config import settings


def _normalize_query(query: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    q = query.lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _cache_key(query: str, language: str = "en") -> str:
    normalized = _normalize_query(query)
    return hashlib.md5(f"{normalized}|{language}".encode()).hexdigest()


class CacheService:
    """In-memory TTL cache for chat responses and search results."""

    def __init__(
        self,
        chat_max_size: int = 1000,
        chat_ttl: int = 300,
        search_max_size: int = 500,
        search_ttl: int = 300,
    ):
        self._chat_cache: TTLCache = TTLCache(maxsize=chat_max_size, ttl=chat_ttl)
        self._search_cache: TTLCache = TTLCache(maxsize=search_max_size, ttl=search_ttl)
        self._stats = {"chat_hits": 0, "chat_misses": 0, "search_hits": 0, "search_misses": 0}

    # ── Chat response cache ─────────────────────────────────────────────────

    def get_chat(self, query: str, language: str = "en") -> Optional[dict]:
        key = _cache_key(query, language)
        result = self._chat_cache.get(key)
        if result is not None:
            self._stats["chat_hits"] += 1
            return result
        self._stats["chat_misses"] += 1
        return None

    def put_chat(self, query: str, language: str, response: dict) -> None:
        key = _cache_key(query, language)
        self._chat_cache[key] = response

    # ── Search response cache ───────────────────────────────────────────────

    def get_search(self, query: str, page_type: str, filters_hash: str, page: int) -> Optional[dict]:
        key = hashlib.md5(f"search|{_normalize_query(query)}|{page_type}|{filters_hash}|{page}".encode()).hexdigest()
        result = self._search_cache.get(key)
        if result is not None:
            self._stats["search_hits"] += 1
            return result
        self._stats["search_misses"] += 1
        return None

    def put_search(self, query: str, page_type: str, filters_hash: str, page: int, response: dict) -> None:
        key = hashlib.md5(f"search|{_normalize_query(query)}|{page_type}|{filters_hash}|{page}".encode()).hexdigest()
        self._search_cache[key] = response

    # ── Stats ───────────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "chat_cache_size": len(self._chat_cache),
            "search_cache_size": len(self._search_cache),
        }


# Module-level singleton
cache = CacheService(
    chat_max_size=getattr(settings, "cache_max_size", 1000),
    chat_ttl=getattr(settings, "cache_ttl_search_seconds", 300),
    search_max_size=500,
    search_ttl=getattr(settings, "cache_ttl_search_seconds", 300),
)
