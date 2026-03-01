# backend/app/models/chat.py
# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request/response models for the chat API.
# Versioned types make it easy to add v2 variants without breaking consumers.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ── Inbound ───────────────────────────────────────────────────────────────────

class MessageItem(BaseModel):
    """Single turn in the conversation history."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """POST /api/chat body."""
    message: str = Field(..., min_length=1, max_length=4096, description="User's message")
    history: List[MessageItem] = Field(default_factory=list, description="Previous turns (last N)")
    session_id: Optional[str] = Field(None, description="Optional session identifier")


# ── Outbound ──────────────────────────────────────────────────────────────────

class ToolCallResult(BaseModel):
    """Metadata about a tool that was invoked (or queued) for this request."""
    tool: str
    status: Literal["queued", "running", "done", "error"] = "queued"
    detail: str = ""


class ChatResponse(BaseModel):
    """POST /api/chat response."""
    reply: str
    citations: List[str] = Field(default_factory=list)
    tool_calls: List[ToolCallResult] = Field(default_factory=list)
    latency_ms: Optional[int] = None
    model: str
    session_id: Optional[str] = None


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    ok: bool
    model_configured: bool
    model_name: str
    model_url: Optional[str]
    es_host: Optional[str]
    version: str


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricsResponse(BaseModel):
    total_requests: int
    avg_latency_ms: float
    tool_calls_total: int
    uptime_seconds: float
