# backend/app/services/translation_fastpath.py
# When the user asks to "translate your previous answer into X", run a single LLM call
# instead of the full agent — no tools, minimal prompt, fast response.
from __future__ import annotations

import re
import time
from typing import Optional, Tuple, List

import structlog

from app.models.chat import MessageItem

log = structlog.get_logger(__name__)

# Match "Translate your previous answer into German" / "translate ... into Spanish" etc.
_TRANSLATE_PATTERN = re.compile(
    r"translate\s+(?:your\s+)?(?:previous\s+)?answer\s+into\s+",
    re.I,
)

_LANG_NAMES = {
    "en": "English",
    "en-us": "English",
    "en-gb": "English",
    "de": "German",
    "es": "Spanish",
    "zh-hans": "Simplified Chinese",
    "zh-hant": "Traditional Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
}


def _last_assistant_content(history: List[MessageItem]) -> Optional[str]:
    """Return the content of the most recent assistant message, or None."""
    for item in reversed(history or []):
        if item.role == "assistant" and item.content and item.content.strip():
            return item.content.strip()
    return None


def try_translation_fastpath(
    message: str,
    history: List[MessageItem],
    language: Optional[str],
) -> Optional[Tuple[str, int]]:
    """
    If the request is to translate the previous answer into another language,
    run a single LLM call (no agent, no tools) and return (translated_reply, latency_ms).
    Otherwise return None.
    """
    msg = (message or "").strip()
    if not msg or not _TRANSLATE_PATTERN.search(msg):
        return None

    target_lang_code = (language or "en").strip().lower()
    target_lang_name = _LANG_NAMES.get(target_lang_code) or "English"

    last_content = _last_assistant_content(history)
    if not last_content or len(last_content) < 10:
        log.info("translation_fastpath.no_previous_answer")
        return None

    # If target is English, return as-is (no LLM) for maximum speed
    if target_lang_code in ("en", "en-us", "en-gb"):
        return (last_content, 0)

    start = time.perf_counter()
    try:
        from app.services.llm_service import build_llm
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = build_llm(profile="default")
        if llm is None:
            return None

        # Minimal prompt: translate only, preserve markdown and links
        system = (
            f"Translate the following text into {target_lang_name}. "
            "Preserve all markdown (headers, lists, bold, links). Do not translate URLs or code. "
            "Output only the translated text, no preamble or explanation."
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=last_content),
        ]
        # Use a shorter timeout for translation so we fail fast
        original_timeout = llm.request_timeout
        llm.request_timeout = 25
        try:
            response = llm.invoke(messages)
            out = (response.content or "").strip()
        finally:
            llm.request_timeout = original_timeout

        if not out:
            return None
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        log.info("translation_fastpath.done", target=target_lang_name, latency_ms=elapsed_ms)
        return (out, elapsed_ms)
    except Exception as e:
        log.warning("translation_fastpath.error", error=str(e))
        return None
