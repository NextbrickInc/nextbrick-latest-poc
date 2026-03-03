# backend/app/routers/chat.py
# POST /api/chat — returns a single JSON response (reply, citations, tool_calls, etc.).
# Frontend expects JSON, not SSE.
from __future__ import annotations
import uuid
import structlog

from fastapi import APIRouter, HTTPException, status
from app.models.chat import ChatRequest, ChatResponse, ToolCallResult
from app.services import agent_service

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _tool_steps_to_citations_and_calls(tool_steps):
    """Build citations and tool_calls for ChatResponse from agent tool_steps."""
    citations = list({step.tool for step in tool_steps})
    seen = set()
    tool_calls = []
    for step in tool_steps:
        if step.tool in seen:
            continue
        seen.add(step.tool)
        count = sum(1 for s in tool_steps if s.tool == step.tool)
        detail = str(step.output)[:200] if step.output else ""
        if count > 1:
            detail = f"used {count}×" + (f" — {detail}" if detail else "")
        tool_calls.append(ToolCallResult(tool=step.tool, status="done", detail=detail or ""))
    return citations, tool_calls


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())[:8]
    bound_log = log.bind(session_id=session_id, message_preview=req.message[:50])
    bound_log.info("chat.request")

    try:
        result = agent_service.invoke_agent(
            message=req.message,
            history=req.history,
            session_id=session_id,
            data_source=req.data_source,
        )
    except Exception as exc:
        bound_log.exception("chat.agent_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent error: {exc}",
        ) from exc

    tool_steps = getattr(result, "tool_steps", []) or []
    citations, tool_calls = _tool_steps_to_citations_and_calls(tool_steps)
    reply = getattr(result, "reply", "") or "No response from agent."
    model = getattr(result, "model", "") or ""
    thinking_steps = getattr(result, "reasoning_steps", []) or []
    input_tokens = getattr(result, "input_tokens", None)
    output_tokens = getattr(result, "output_tokens", None)

    return ChatResponse(
        reply=reply,
        citations=citations,
        tool_calls=tool_calls,
        thinking_steps=thinking_steps,
        latency_ms=getattr(result, "latency_ms", None),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        session_id=session_id,
    )
