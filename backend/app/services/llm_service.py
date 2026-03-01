# backend/app/services/llm_service.py
# ─────────────────────────────────────────────────────────────────────────────
# LLM initialisation and invocation with retry / timeout logic.
# Wraps LangChain's ChatOpenAI so we can swap models by changing .env alone.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import structlog
from typing import Optional, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.models.chat import MessageItem

log = structlog.get_logger(__name__)

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a helpful enterprise AI assistant for the Nextbrick Agentic AI POC. "
    "You have access to data from Salesforce (cases, orders), Confluence (knowledge articles), "
    "AEM DAM (product manuals, datasheets), and Elasticsearch (semantic search). "
    "Answer concisely with citations where possible. "
    "For real-time data (pricing, order status, case creation), "
    "indicate which tool you would invoke. "
    "Support English, German, Spanish, and Chinese."
)


# ── URL normalisation ─────────────────────────────────────────────────────────

def _normalize_base_url(raw: str) -> str:
    """
    Ensure the URL ends with /v1 (required by langchain-openai).
    Handles Ollama (port 11434), vLLM, and standard OpenAI-compat servers.
    """
    url = raw.rstrip("/")
    for suffix in ("/chat/completions", "/completions", "/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return f"{url}/v1"


# ── LLM Factory ───────────────────────────────────────────────────────────────

def build_llm() -> Optional[ChatOpenAI]:
    """
    Return a configured ChatOpenAI client or None if no model URL is set.
    The client is OpenAI-API-compatible and works with Ollama, vLLM, etc.
    """
    raw_url = settings.effective_model_url
    if not raw_url:
        log.warning("llm_service.no_url_configured")
        return None

    base_url = _normalize_base_url(raw_url)
    model_name = settings.effective_model_name
    api_key = settings.effective_api_key

    log.info(
        "llm_service.build_llm",
        base_url=base_url,
        model_name=model_name,
    )

    return ChatOpenAI(
        model=model_name,
        temperature=settings.llm_temperature,
        openai_api_key=api_key,
        openai_api_base=base_url,
        request_timeout=settings.llm_timeout_seconds,
        max_retries=0,  # retries handled by tenacity below
    )


# ── Message Builder ───────────────────────────────────────────────────────────

def build_messages(history: List[MessageItem], new_message: str) -> List:
    """Prepend system prompt and convert history into LangChain message objects."""
    msgs: List = [SystemMessage(content=SYSTEM_PROMPT)]
    # Keep last 8 turns to stay within context window
    for item in history[-8:]:
        if item.role == "user":
            msgs.append(HumanMessage(content=item.content))
        else:
            msgs.append(AIMessage(content=item.content))
    msgs.append(HumanMessage(content=new_message))
    return msgs


# ── Invoke with retry ─────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(settings.llm_max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def invoke_llm(llm: ChatOpenAI, messages: List) -> str:
    """
    Call the LLM and return the text content.
    Tenacity retries up to `llm_max_retries` times with exponential backoff.
    """
    response = llm.invoke(messages)
    return response.content or ""
