# backend/app/services/generated_answer_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Generates an AI answer from top search results (RAG-lite).
# Uses a small, focused prompt with a 5s timeout for fast responses.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import structlog
from typing import Optional

from app.models.search import SearchResult
from app.services.llm_service import build_llm

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are a helpful Keysight Technologies support assistant.
Based on the provided search results, give a concise, accurate answer to the user's question.
If the search results don't contain enough information, say so briefly.
Keep your answer under 200 words. Use markdown formatting for clarity.
Do NOT make up information not present in the search results."""


def generate_answer(query: str, results: list[SearchResult], language: str = "en") -> Optional[str]:
    """
    Generate a concise answer from the top search results.
    Returns None if LLM is unavailable or times out.
    """
    if not results:
        return None

    try:
        llm = build_llm(profile="default")
        if llm is None:
            return None

        # Build context from top 3 results
        context_parts = []
        for i, r in enumerate(results[:3], 1):
            context_parts.append(
                f"[{i}] Title: {r.title}\n"
                f"Description: {r.description[:400]}\n"
                f"Category: {r.category or 'N/A'}\n"
            )

        context = "\n---\n".join(context_parts)
        lang_note = f"\nRespond in {language}." if language != "en" else ""

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Search results:\n{context}\n\nQuestion: {query}{lang_note}"},
        ]

        from langchain_core.messages import SystemMessage, HumanMessage
        lc_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
        ]

        response = llm.invoke(lc_messages)
        return response.content if hasattr(response, "content") else str(response)

    except Exception as e:
        log.warning("generated_answer.failed", error=str(e), query=query[:50])
        return None
