# backend/app/routers/chat.py
# POST /api/chat — returns a single JSON response (reply, citations, tool_calls, etc.).
# Frontend expects JSON, not SSE.
from __future__ import annotations
import uuid
import time
import structlog

from fastapi import APIRouter, HTTPException, status
from app.models.chat import ChatRequest, ChatResponse, ToolCallResult
from app.services import agent_service
from app.services.manual_fastpath import build_manual_fastpath_reply, try_manual_websearch_fastpath
from app.services.data_fastpath import try_data_fastpath, try_status_intent_fastpath
from app.services.translation_fastpath import try_translation_fastpath
from app.services.product_fastpath import try_product_spec_fastpath
from app.services.faq_fastpath import try_faq_fastpath
from app.services.cache_service import cache
from app.services.support_case_fastpath import try_support_case_fastpath

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
    started = time.perf_counter()

    # ── Cache check — serves repeated queries in <10ms ──────────────────────
    cached = cache.get_chat(req.message, req.language or "en")
    if cached:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            **{**cached, "latency_ms": elapsed_ms, "session_id": session_id, "model": cached.get("model", "cache-v1")}
        )

    # ── FAQ fast-path — precomputed answers for common questions (<10ms) ────
    faq_fast = try_faq_fastpath(req.message, req.language)
    if faq_fast:
        reply_text, citations_list = faq_fast
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        resp = ChatResponse(
            reply=reply_text,
            citations=citations_list,
            tool_calls=[],
            thinking_steps=["Matched precomputed FAQ answer; served instantly."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="faq-cache-v1",
            session_id=session_id,
        )
        cache.put_chat(req.message, req.language or "en", resp.model_dump(exclude={"session_id"}))
        return resp

    # ── Support case fast-path — direct parse + direct Salesforce create ────
    case_create_fast = try_support_case_fastpath(req.message, req.language)
    if case_create_fast:
        reply_text, citations_list = case_create_fast
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        resp = ChatResponse(
            reply=reply_text,
            citations=citations_list,
            tool_calls=[],
            thinking_steps=["Support-case fast path: skipped agent loop."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="support-case-fastpath-v1",
            session_id=session_id,
        )
        cache.put_chat(req.message, req.language or "en", resp.model_dump(exclude={"session_id"}))
        return resp

    # Sub-second path: U1610A manual (no LLM, no network) — check first
    fast_reply = build_manual_fastpath_reply(req.message, req.language)
    if fast_reply:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            reply=fast_reply,
            citations=["manual_fastpath"],
            tool_calls=[],
            thinking_steps=["Detected known manual lookup pattern; served deterministic fast-path response."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="manual-fastpath-v1",
            session_id=session_id,
        )

    # Product spec fast path: avoid generic document answers for known product-spec prompts
    product_fast = try_product_spec_fastpath(req.message, req.language)
    if product_fast:
        reply_text, citations_list = product_fast
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        tool_calls_list = [ToolCallResult(tool=c, status="done", detail="") for c in citations_list]
        return ChatResponse(
            reply=reply_text,
            citations=citations_list,
            tool_calls=tool_calls_list,
            thinking_steps=["Detected product-spec query and served product-focused fast-path response."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="product-fastpath-v1",
            session_id=session_id,
        )

    bound_log = log.bind(session_id=session_id, message_preview=req.message[:50])
    bound_log.info("chat.request")

    # Product-manual websearch fast path: any manual/doc lookup — one elasticsearch_websearch call, no agent
    manual_web = try_manual_websearch_fastpath(req.message, req.language)
    if manual_web:
        reply_text, citations_list = manual_web
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        tool_calls_list = [ToolCallResult(tool=c, status="done", detail="") for c in citations_list]
        return ChatResponse(
            reply=reply_text,
            citations=citations_list,
            tool_calls=tool_calls_list,
            thinking_steps=["Fast path: searched product docs with elasticsearch_websearch (no agent)."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="manual-websearch-fastpath-v1",
            session_id=session_id,
        )

    # Translation fast path: "translate previous answer into X" — single LLM call, no agent/tools
    trans = try_translation_fastpath(req.message, req.history, req.language)
    if trans is not None:
        reply_text, elapsed_ms = trans
        elapsed_ms = elapsed_ms or int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            reply=reply_text,
            citations=["translation_fastpath"],
            tool_calls=[],
            thinking_steps=["Translated previous answer via single LLM call (no tools)."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="translation-fastpath-v1",
            session_id=session_id,
        )

    # Status-intent fast path: case/order status asked without ID -> instant guidance (no LLM)
    intent_fast = try_status_intent_fastpath(req.message)
    if intent_fast:
        reply_text, citations_list = intent_fast
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            reply=reply_text,
            citations=citations_list,
            tool_calls=[],
            thinking_steps=["Detected status intent without identifier; requested missing case/order number."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="status-intent-fastpath-v1",
            session_id=session_id,
        )

    # Data fast path: case/order/cal-cert by ID — one tool call, no LLM
    data_fast = try_data_fastpath(req.message)
    if data_fast:
        reply_text, citations_list = data_fast
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        tool_calls_list = [ToolCallResult(tool=c, status="done", detail="") for c in citations_list]
        resp = ChatResponse(
            reply=reply_text,
            citations=citations_list,
            tool_calls=tool_calls_list,
            thinking_steps=[f"Fast path: queried {', '.join(citations_list)} directly."],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="data-fastpath-v1",
            session_id=session_id,
        )
        # Cache case/order/cal-cert responses so repeated queries are ~10ms
        cache.put_chat(req.message, req.language or "en", resp.model_dump(exclude={"session_id"}))
        return resp

    try:
        result = agent_service.invoke_agent(
            message=req.message,
            history=req.history,
            session_id=session_id,
            data_source=req.data_source,
            language=req.language,
        )
    except Exception as exc:
        bound_log.exception("chat.agent_error", error=str(exc))
        err_msg = str(exc).strip().lower()
        if "timed out" in err_msg or "timeout" in err_msg:
            friendly = (
                "The request took too long and timed out. Try a shorter question, "
                "or try again later. You can also ask for **case status**, **order status**, or **cal certificate** by number for a faster response."
            )
        else:
            friendly = f"Something went wrong: {exc}. Please try again."
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            reply=friendly,
            citations=[],
            tool_calls=[],
            thinking_steps=[],
            latency_ms=elapsed_ms,
            input_tokens=None,
            output_tokens=None,
            model="",
            session_id=session_id,
        )

    tool_steps = getattr(result, "tool_steps", []) or []
    citations, tool_calls = _tool_steps_to_citations_and_calls(tool_steps)
    reply = getattr(result, "reply", "") or "No response from agent."
    model = getattr(result, "model", "") or ""
    thinking_steps = getattr(result, "reasoning_steps", []) or []
    input_tokens = getattr(result, "input_tokens", None)
    output_tokens = getattr(result, "output_tokens", None)

    resp = ChatResponse(
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

    # Cache successful agent responses for repeated queries
    if reply and not reply.startswith("Something went wrong"):
        cache.put_chat(req.message, req.language or "en", resp.model_dump(exclude={"session_id"}))

    return resp
