# backend/app/services/tool_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Lightweight keyword-based tool router for the POC.
# In production this becomes a LangGraph agent with real tool nodes.
# Each tool returns a ToolCallResult that gets sent to the frontend as metadata.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from typing import List

from app.models.chat import ToolCallResult


# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOL_RULES: List[tuple[tuple[str, ...], str, str]] = [
    # (keywords_any, tool_name, detail)
    (("price", "pricing", "cost", "how much"),        "pricing.lookup",             "region=US, source=PIM"),
    (("where is my order", "order status", "order"),  "salesforce.order_status",    "object=Order"),
    (("create a case", "create case", "open a case"), "salesforce.case.create",     "priority=standard"),
    (("case status", "case",),                        "salesforce.case.status",     "object=Case"),
    (("service order status", "service order"),       "salesforce.service_order",   "object=ServiceOrder"),
    (("cal certificate", "calibration", "certificate"), "calibration.lookup",       "object=Asset"),
    (("send email", "email customer"),                "email.send",                 "recipient=customer"),
    (("instruction manual", "product manual", "manual", "pdf"), "aem.document_search", "type=manual"),
    (("knowledge",),                                  "confluence.knowledge_search","type=article"),
    (("snowflake",),                                  "snowflake.query",            "warehouse=compute_wh"),
    (("salesforce",),                                 "salesforce.generic",         "org=prod"),
]


def infer_tool_calls(text: str) -> List[ToolCallResult]:
    """
    Score the user message against the rule table.
    Returns a de-duplicated, ordered list of ToolCallResult objects.
    Falls back to elasticsearch.search if no rule matches.
    """
    lowered = text.lower()
    seen: set[str] = set()
    results: List[ToolCallResult] = []

    for keywords, tool_name, detail in _TOOL_RULES:
        if any(kw in lowered for kw in keywords):
            if tool_name not in seen:
                seen.add(tool_name)
                results.append(
                    ToolCallResult(tool=tool_name, status="queued", detail=detail)
                )

    if not results:
        results.append(
            ToolCallResult(
                tool="elasticsearch.search",
                status="queued",
                detail="mode=semantic",
            )
        )

    return results
