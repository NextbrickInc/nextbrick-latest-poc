# backend/app/routers/chat.py
# ─────────────────────────────────────────────────────────────────────────────
# POST /api/chat — main agentic response endpoint.
# Wires together: LLM service → tool service → metrics recording.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import time
import uuid
import structlog

from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.models.chat import ChatRequest, ChatResponse
from app.services.llm_service import build_llm, build_messages, invoke_llm
from app.services.tool_service import infer_tool_calls
from app.middleware.metrics import metrics_store

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

_DEMO_CITATIONS = ["AEM DAM", "Confluence", "Salesforce"]


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Process a user message:
    1. Run tool-routing heuristic
    2. Call LLM (with retry) or return demo response if no model configured
    3. Record metrics
    4. Return structured response
    """
    session_id = req.session_id or str(uuid.uuid4())[:8]
    bound_log = log.bind(session_id=session_id, message_preview=req.message[:50])
    bound_log.info("chat.request")

    tool_calls = infer_tool_calls(req.message)
    model_name = settings.effective_model_name

    # ── Demo mode (no LLM configured) ────────────────────────────────────────
    llm = build_llm()
    if llm is None:
        bound_log.warning("chat.demo_mode")
        return ChatResponse(
            reply=(
                f"[Demo mode — model URL not configured] "
                f"I would search indexed sources and invoke tools for: \"{req.message}\"."
            ),
            citations=_DEMO_CITATIONS,
            tool_calls=tool_calls,
            latency_ms=None,
            model=model_name,
            session_id=session_id,
        )

    # ── Live LLM call ─────────────────────────────────────────────────────────
    messages = build_messages(req.history, req.message)
    start = time.perf_counter()

    try:
        reply_text = invoke_llm(llm, messages)
    except Exception as exc:
        bound_log.exception("chat.llm_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM error: {exc}",
        ) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    bound_log.info("chat.response", latency_ms=latency_ms, tools=len(tool_calls))

    # Record metrics
    metrics_store.record(latency_ms=latency_ms, tool_calls=len(tool_calls))

    return ChatResponse(
        reply=reply_text or "No response from model.",
        citations=[],
        tool_calls=tool_calls,
        latency_ms=latency_ms,
        model=model_name,
        session_id=session_id,
    )
