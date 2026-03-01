import os
import time
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


load_dotenv()

app = FastAPI(title="Nextbrick Agentic AI Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = None


class ToolCall(BaseModel):
    tool: str
    status: str
    detail: str


class ChatResponse(BaseModel):
    reply: str
    citations: List[str]
    tool_calls: List[ToolCall]
    latency_ms: Optional[int]
    model: str


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_model_name() -> str:
    return (
        os.getenv("ONPREM_MODEL_NAME")
        or os.getenv("MODEL_NAME")
        or "qwen2.5-coder:latest"
    )


def normalize_base_url(raw_url: str) -> str:
    """
    Normalise a raw URL to end with /v1 for the OpenAI-compatible endpoint.
    Ollama exposes OpenAI-compatible API at http://localhost:11434/v1.
    """
    url = raw_url.rstrip("/")
    # Strip any trailing path components beyond the host
    for suffix in ("/chat/completions", "/completions", "/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return f"{url}/v1"


def build_llm() -> Optional[ChatOpenAI]:
    base_url = os.getenv("ONPREM_MODEL_URL") or os.getenv("MODEL_URL", "")
    if not base_url:
        return None
    base_url = normalize_base_url(base_url)
    model_name = get_model_name()
    api_key = (
        os.getenv("ONPREM_MODEL_API_KEY")
        or os.getenv("MODEL_API_KEY")
        or "EMPTY"
    )
    return ChatOpenAI(
        model=model_name,
        temperature=0.2,
        openai_api_key=api_key,
        openai_api_base=base_url,
    )


def infer_tool_calls(text: str) -> List[ToolCall]:
    """
    Lightweight keyword-based tool router.
    In a production agentic setup these would be real LangGraph tool nodes.
    """
    lowered = text.lower()
    calls: List[ToolCall] = []
    if "price" in lowered or "pricing" in lowered:
        calls.append(ToolCall(tool="pricing.lookup", status="queued", detail="region=US"))
    if "order" in lowered:
        calls.append(ToolCall(tool="salesforce.order_status", status="queued", detail="order_id=lookup"))
    if "case" in lowered and "create" in lowered:
        calls.append(ToolCall(tool="salesforce.case.create", status="queued", detail="priority=standard"))
    elif "case" in lowered:
        calls.append(ToolCall(tool="salesforce.case.status", status="queued", detail="case_id=lookup"))
    if "cal" in lowered or "certificate" in lowered:
        calls.append(ToolCall(tool="calibration.lookup", status="queued", detail="asset_id=lookup"))
    if "service order" in lowered:
        calls.append(ToolCall(tool="salesforce.service_order", status="queued", detail="so_id=lookup"))
    if "email" in lowered or "send" in lowered:
        calls.append(ToolCall(tool="email.send", status="queued", detail="recipient=customer"))
    if "manual" in lowered or "instruction" in lowered:
        calls.append(ToolCall(tool="aem.document_search", status="queued", detail="type=manual"))
    if not calls:
        calls.append(ToolCall(tool="elasticsearch.search", status="queued", detail="semantic_search=true"))
    return calls


def build_messages(history: List[Message], message: str) -> List:
    messages = [
        SystemMessage(
            content=(
                "You are a helpful enterprise AI assistant for the Nextbrick Agentic AI POC. "
                "You have access to data from Salesforce (cases, orders), Confluence (knowledge articles), "
                "AEM DAM (product manuals, datasheets), and Elasticsearch (semantic search). "
                "Answer concisely with citations where possible. "
                "For real-time data (pricing, order status, case creation), indicate which tool you would call. "
                "Support English, German, Spanish, and Chinese."
            )
        )
    ]
    for item in history[-8:]:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=message))
    return messages


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/api/health")
def health():
    model_configured = bool(
        os.getenv("ONPREM_MODEL_URL") or os.getenv("MODEL_URL")
    )
    return {
        "ok": True,
        "model_configured": model_configured,
        "model_name": get_model_name(),
        "model_url": os.getenv("ONPREM_MODEL_URL") or os.getenv("MODEL_URL") or None,
        "es_host": os.getenv("ES_HOST") or None,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    llm = build_llm()
    history = req.history or []
    tool_calls = infer_tool_calls(req.message)
    model_name = get_model_name()

    if llm is None:
        reply = (
            f"[Demo mode – no model URL configured] "
            f"I would search indexed manuals and run tool calls for: \"{req.message}\"."
        )
        return ChatResponse(
            reply=reply,
            citations=["AEM DAM", "Confluence", "Salesforce"],
            tool_calls=tool_calls,
            latency_ms=None,
            model=model_name,
        )

    start = time.time()
    response = llm.invoke(build_messages(history, req.message))
    latency_ms = int((time.time() - start) * 1000)

    return ChatResponse(
        reply=response.content or "No response from model.",
        citations=[],
        tool_calls=tool_calls,
        latency_ms=latency_ms,
        model=model_name,
    )
