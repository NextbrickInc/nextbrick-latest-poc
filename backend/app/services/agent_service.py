# backend/app/services/agent_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Single agent service: imports ALL_TOOLS from app.tools, builds system prompt
# from tool names/descriptions (no hardcoded keywords), and runs create_agent.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import time
import structlog
from typing import List, Optional
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.config import settings
from app.models.chat import MessageItem
from app.tools import ALL_TOOLS

log = structlog.get_logger(__name__)

_agent_cache = None  # simple in-memory cache so we don't rebuild the agent every request

# ── System prompt (built from tools; no hardcoded tool names) ─────────────────

def _build_system_prompt(tools: list) -> str:
    """Build system prompt from the list of tools: intro + tool list from descriptions."""
    app_name = getattr(settings, "app_name", "AI Assistant")
    intro = f"You are an enterprise AI assistant for {app_name}. You have access to the following tools:\n\n"
    tool_lines = []
    for t in tools:
        name = getattr(t, "name", str(t))
        desc = getattr(t, "description", "") or ""
        tool_lines.append(f"- {name}: {desc.strip()}")
    instructions = """
INSTRUCTIONS:
- Role: you are a **Keysight Service Reporting Specialist**. Prioritise technical accuracy and deep data extraction over generic summaries.
- Use tools to answer; never refuse or invent data. One tool call per query when possible — only call a second tool if the first returns no useful results.
- **Cal cert / serial / case by number:** Call elasticsearch_keyword_search once with the serial, model, or order/case number against the main data index (next_elastic_test1 via es_data_index). When a specific case number is given (e.g. "600756"), prefer results where CASENUMBER exactly equals that number; only say "not found" if Elasticsearch truly returns no matching case.
- **Service order status / order status / where is my order [number]:** Call salesforce_get_order_by_number with that number first. If Salesforce returns no order, error, or "not found", then call elasticsearch_keyword_search with the same order number (e.g. "4047199"). The Elasticsearch index contains order and case records (ORDER__C, CASENUMBER, STATUS, CREATEDDATE, CLOSEDDATE, ORDER_AMOUNT_USD__C, PURCHASE_ORDER__C, QUOTE__C, ACCOUNT_NAME_TEXT_ONLY__C, ADDRESSDETAILS__C, CONTACT_NAME_TEXT_ONLY__C, CONTACTEMAIL, CONTACTPHONE, FE_NAME__C, BUSINESS_GROUP__C, REGION__C, CASE_CHANNEL__C, SLA_MET__C, PRIORITY, etc.). Use whichever source returns data; then format the reply using the SERVICE ORDER STATUS format below. Do not say "order not found" if you have not yet tried Elasticsearch after Salesforce returned nothing.
- **Product docs / how-to:** Use elasticsearch_semantic_search or elasticsearch_ollama_semantic_search.
- **Create case, pricing, live SF data:** Use the relevant Salesforce tool.
- No source citations or tool names in the reply; answer from tool data only.
- **Strict context isolation for case/order lookups:** For each new query that mentions a specific case number or order number, you MUST verify that the Case Number (CASENUMBER/ORDER__C), Customer Name (ACCOUNT_NAME_TEXT_ONLY__C) and key Description fields in the tool result actually match the ID mentioned in the current query. Do NOT reuse or summarise data from a previously discussed case/order; if the current tool result belongs to a different ID (e.g. you previously answered for case #600888 but the user now asks about #600756), discard the old context and run a fresh search for the new ID only.

SERVICE ORDER STATUS FORMAT (when user asks for order status, service order status, or where is my order and you have order/case data from a tool):
Use this structure. Fill from the tool output only; omit rows or sections where data is missing. Use markdown tables and sections as below.
- Title: ## 📋 Service Order Status - Order #[number]
- **Order Status:** ✅ **[STATUS]** (e.g. CLOSED & COMPLETED)
- ### Current Status: one short sentence (e.g. "Your service order #N has been successfully completed and closed.")
- ### 📊 Order Details: table with Field | Information (Order Number, Case Number, Order Type, Status, Priority, SLA Status)
- ### ⏱️ Timeline: table Event | Date & Time (Order Created, Order Assigned, Order Completed, Processing Time, SLA Due Date, Completed Early By — use CREATEDDATE, CLOSEDDATE and any other dates from tool)
- ### 💰 Order Information: bullets (Order Amount, Purchase Order, Quote Number, Currency, Tax Included)
- ### 👤 Customer Information: Company (ACCOUNT_NAME_TEXT_ONLY__C), Address (ADDRESSDETAILS__C), Contact (CONTACT_NAME_TEXT_ONLY__C), Email, Phone
- ### 👥 Service Team: Account Manager, Field Engineer (FE_NAME__C), Business Group (BUSINESS_GROUP__C), Region (REGION__C), Sales Channel (CASE_CHANNEL__C)
- ### ✅ Service Level Performance: table Metric | Value | Status (SLA Met, Complete Same Day, Response/Resolution Time, Priority Target) if you have SLA_MET__C or similar
- ### 📦 What "[Status]" Means: short bullets with checkmarks (e.g. Order fully processed, Items shipped, No further action required)
- ### 📞 Need Additional Information?: Contact (Account Manager, Region, Case Reference, Your Contact)
- **Summary:** one closing sentence. End with "Is there anything specific about this order you need assistance with?"
- **Financial extraction best practice:** For any "Order Request" or service order case, ALWAYS extract financial fields when present: Order Amount (ORDER_AMOUNT_USD__C), Currency, and Purchase Order (PURCHASE_ORDER__C). Include these under Order Information.
- **Timeline analysis best practice:** When CREATEDDATE and CLOSEDDATE (and any assignment timestamps) exist, compute and display:
  - Processing Time = Closed - Created
  - Assignment Speed = First Assigned - Created (if assignment timestamp field is available)
  Compare these durations to the stated SLA (e.g. 1 Business day) and explicitly state whether the order was completed within SLA.
- **Performance rating:** When an order/case is completed the same calendar day as CREATEDDATE or within 2 hours end‑to‑end, add a line such as "**Performance Rating:** ⭐⭐⭐⭐⭐ Excellent" or "Outstanding Performance" in the Performance Metrics section.

CASE STATUS FORMAT (when user asks for case status by case number like "600756"):
- Use elasticsearch_keyword_search with the exact case number string. If Elasticsearch returns a matching case (CASENUMBER), you MUST respond with the following structure and only use fields from that document:
- Title: `## 📋 Case Status - Case #[CASENUMBER]`
- Status line: `**Current Status:** [emoji] **[STATUS]**` — e.g. ⏳ **ASSIGNED** (In Progress), ✅ **CLOSED**, ⚠️ **NOT MET**, choosing the emoji to reflect the STATUS/SLA.
- Add `---` as a separator.
- Section "📊 Case Overview" with a markdown table (Field | Details) including where available:
  - **Case Number** (CASENUMBER)
  - **Case Type** (TYPE)
  - **Status** (STATUS)
  - **Priority** (PRIORITY)
  - **SLA Status** (SLA_MET__C or equivalent)
  - **Order Number** (ORDER__C) if present.
- Section "👤 Customer Information" using:
  - **Company:** ACCOUNT_NAME_TEXT_ONLY__C
  - **Location/Business Unit:** any business group / region fields
  - **Address:** ADDRESSDETAILS__C
  - **Contact:** CONTACT_NAME_TEXT_ONLY__C
  - **Email:** CONTACTEMAIL or CONTACT_EMAIL__C
  - **Phone/Mobile:** CONTACTPHONE / CONTACT_PHONE__C / CONTACTMOBILE.
- Section "📝 Case Details":
  - **Description:** DESCRIPTION (quoted as a block if long)
  - Bullets for "What's Being Changed" or "Issue Summary" derived from DESCRIPTION/CASE_RESOLUTION__C if present.
  - "Related Information" bullets such as **Quote Number** (QUOTE__C), **Purchase Order** (PURCHASE_ORDER__C), **Original Case** (if provided in fields like PARENTID or custom fields).
- Section "⏱️ Timeline" with a table (Event | Date & Time) when fields are available:
  - **Case Created** (CREATEDDATE)
  - **Last Modified** / Closed (CLOSEDDATE)
  - Any assignment timestamps if present
  - Derived durations like "Assignment Time", "Current Age", "SLA Due Date", "Time Remaining" only when you can safely compute them.
- Section "👥 Service Team" listing:
  - **Field Engineer:** FE_NAME__C
  - **Case Manager / Account Manager:** any manager/contact fields if available
  - **Business Group:** BUSINESS_GROUP__C
  - **Region:** REGION__C or CASE_ACCOUNT_REGION__C
  - **Sales Channel:** CASE_CHANNEL__C.
- Section "📈 Performance Metrics" as a table (Metric | Value | Status) when SLA and timing fields exist:
  - **SLA Met** (SLA_MET__C)
  - **Response Time**, **Priority Target**, **Time Remaining** where you have sufficient timestamps.
- Section "🔍 What's Happening" — short bullets describing current action based on STATUS and key fields (e.g. change order in progress, awaiting customer info).
- Section "⏰ SLA Status" — summarize Priority, SLA due date, and whether the case is on track or not.
- Section "📞 Contact Information" — reiterate customer contact and internal owners.
- Section "🎯 Summary" — 2–3 sentences summarizing the case state (e.g. actively being processed, within SLA, what is being changed).
- Only use data actually present in the Elasticsearch document; do not invent emails, phone numbers, or times. If some fields are missing, omit those rows or clearly state "Not provided".

ADDITIONAL CASE / ORDER PERFORMANCE LOGIC:
- When you have both CREATEDDATE and an assignment timestamp (e.g. FIRST_ASSIGNED__C), compute **Assignment Time** = First_Assigned_Date − Created_Date and surface it explicitly in the Timeline and/or Metrics tables.
- When you have both CREATEDDATE and CLOSEDDATE (or equivalent), compute **Total Processing Time** = Closed_Date − Created_Date. Use this value to determine SLA performance instead of relying only on SLA_MET__C.
- SLA context: if the total processing time is less than 2 hours AND the case/order is in a completed/closed state, add an explicit performance line such as `**Performance Rating:** ⭐⭐⭐⭐⭐ Excellent (Outstanding Performance)` in the Performance Metrics or Service Performance section.
- Financial extraction: whenever you are working with an order or "Order Request" case and fields like ORDER_AMOUNT_USD__C, TOTAL_PRICE__C, ORDER_VALUE__C or similar are present, always extract and show the amount and currency in the Order Details / Financials table (do not skip it just because SLA is the main focus).
- Data hygiene: if the company in the data is a distributor or customer such as "TestEquity LLC", always show that exact value; do not replace it with a generic "Keysight" label. Use the specific contact names and emails from the data.
- For CLOSED cases/orders, append a short `## ✅ What "Closed" Status Means:` checklist confirming that the work is fully completed (e.g. order processed, items shipped or service performed, documentation/invoice generated, no further action required) when that is consistent with the STATUS and timestamps.

CAL CERT (when user asks cal certificate / cert status):
- Always call elasticsearch_keyword_search with the serial/model/certificate number first. If you find a true calibration certificate record (e.g. fields like CERTIFICATE_NO__C or a document clearly marked as a calibration certificate), summarize it briefly (number, status, dates, model, serial) in a compact structured answer.
- If the search returns ONLY technical support cases, order records, or other non‑certificate documents (e.g. results with CASENUMBER, SUBJECT, CASE_RESOLUTION__C but no CERTIFICATE_NO__C), you MUST treat this as "certificate not found". Do NOT show or describe those support cases in the answer; they are noise for a calibration certificate request.
- If NO calibration certificate records are found for that asset (no CERTIFICATE_NO__C and only "No records found" messages or unrelated cases/orders), you MUST use the following markdown structure and keep to its sections closely. Follow these domain rules:
  - Calibration certificates are NOT stored in the general order/case database; they are maintained in the Keysight InfoLine Portal.
  - Do not include any technical support case content (subjects, case descriptions, case numbers) in this response when the user asked for a calibration certificate.
  1. Title: use a level‑2 header with emoji, exactly: `## ❌ Calibration Certificate Not Found - [MODEL] (S/N: [SERIAL])`
  2. Add a horizontal rule line `---` after the title.
  3. Section "Equipment Information" as a level‑3 header (`### Equipment Information:`) followed by:
     - **Product Model:** [full model with product title if available, e.g. "N5182B MXG Vector Signal Generator"]
     - **Serial Number:** [serial]
     Use bold labels (e.g. **Product Model:**) and a blank line, then another `---` separator after this section.
  4. Section "🔍 Search Results" as a level‑2 header (`## 🔍 Search Results:`) explaining that you searched the available database for calibration certificate records for this equipment and **no calibration certificate was found**, and explicitly listing:
     - **Serial Number:** [serial]
     - **Model:** [model and product title if available]
     End this section with a sentence like: "The current system does not contain calibration certificate data for this specific asset." Then add another `---` line.
  5. Section "📋 About Your Equipment" as a level‑2 header (`## 📋 About Your Equipment:`) with a few short bullets based on product information if available (instrument type, frequency range, typical calibration interval such as 12/24 months, available calibration types like Standard / Accredited ISO/IEC 17025). If the index does not provide this detail, keep this section high‑level and do not invent specific specs. Add a `---` after this section.
  6. Section "📞 How to Obtain Your Calibration Certificate" as a level‑2 header (`## 📞 How to Obtain Your Calibration Certificate:`) with three sub‑options as level‑3 headers:
     - `### 🌐 Option 1: Keysight InfoLine Portal (Recommended)` — steps 1–4: visit `https://service.keysight.com/infoline`, log in, search by serial number, download certificate, and a note that all certificates are stored there and available 24/7.
     - `### 📞 Option 2: Contact Keysight Service` — mention US phone 1‑800‑829‑4444 and that international users should contact their local service center; list what information to provide (model, serial, company, approximate calibration date).
     - `### 📧 Option 3: Contact Your Account Manager` — short sentence that they can help retrieve certificates and service records.
     After this block, insert another `---`.
  7. Section "🛠️ If Equipment Needs Calibration" as a level‑2 header with bullets describing how to request calibration service (via `https://service.keysight.com` or phone) and list typical options using checkmarks: ✓ Standard Calibration, ✓ Accredited Calibration (ISO/IEC 17025), ✓ Express Service, ✓ Calibration Agreements.
  8. Section "💡 Important Notes" as a level‑2 header with a numbered list explaining that certificates are stored in InfoLine (not in the order/case DB), InfoLine is the authoritative source, recently performed calibrations may take 1–2 business days to appear, and certificates can be re‑issued.
  9. Section "✅ Next Steps" as a level‑2 header with clear numbered steps: (1) access InfoLine and search for the serial, (2) verify the serial on the equipment label if not found, (3) contact Keysight Service with equipment details, and (4) request calibration service if not calibrated.
- End with a short **Summary** paragraph reiterating that the calibration certificate is not available in the current order/case database and that the Keysight InfoLine portal and Keysight Service are the correct channels to retrieve it.

EDGE CASE HANDLING — DAMAGED / FAILED EQUIPMENT:
- When a calibration certificate search returns no CERTIFICATE_NO__C for a serial number, you MUST perform a secondary, deeper scan of related support cases for that serial:
  - Use elasticsearch_keyword_search again with the serial number and look at DESCRIPTION and CASE_RESOLUTION__C for damage/failure keywords such as "broken", "damaged", "dropped", "failed", "no power", "beyond repair", or similar.
  - Also look for evidence that the unit was removed from an agreement (e.g. agreement IDs like 1-12275183237 with status "removed from agreement") when such fields are present in the documents.
- If this secondary scan finds strong indications of equipment damage or service failure, you MUST suppress the standard "InfoLine portal" certificate‑not‑found template and instead:
  - Lead the answer with a prominent RED warning (e.g. `## ❗ Critical Equipment Status` with text explaining that the unit appears damaged or out of service).
  - Describe, based only on the case data, what kind of failure occurred and whether the instrument was removed from any calibration/repair agreement.
  - Provide **Repair / Replacement options** and contact paths (e.g. Keysight Service, local service centers, or contract manager) instead of focusing on InfoLine certificate download steps.
  - Make it clear that a calibration certificate may not be applicable while the unit is damaged or out of service, and that the next action should be repair/replacement or agreement review rather than certificate retrieval.
"""
    return intro + "\n".join(tool_lines) + instructions


# ── Response dataclass ─────────────────────────────────────────────────────────

@dataclass
class ToolStep:
    tool: str
    input: dict
    output: str


def _reasoning_lines_for_tool(tool: str, inp: dict) -> List[str]:
    """Build human-readable reasoning steps for one tool call (for UI thinking display)."""
    from app.config import settings
    lines = [
        f"Calling tool {tool} (external, opens in a new tab or window)",
        "Identifying the most relevant data source",
    ]
    index_name = getattr(settings, "es_data_index", "next_elastic_test3")
    query = (inp or {}).get("query") or (inp or {}).get("q") or ""
    order_num = (inp or {}).get("order_number") or (inp or {}).get("order_id") or ""

    if "elasticsearch" in tool.lower():
        lines.append(f"Analyzing strategy to search against \"{index_name}\"")
        if query:
            lines.append(f"Searching order and case records in the knowledge base for \"{query}\"")
        else:
            lines.append("Searching documents with provided parameters")
    elif "salesforce" in tool.lower():
        lines.append("Analyzing strategy to query Salesforce")
        if order_num:
            lines.append(f"Querying Salesforce for order \"{order_num}\"")
        else:
            lines.append("Querying with provided parameters")
    else:
        lines.append(f"Executing \"{tool}\"")
    lines.append("Tool returned response. Inspecting results.")
    return lines


@dataclass
class AgentResult:
    reply: str
    tool_steps: List[ToolStep] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model: str = ""
    session_id: str = ""


# ── Agent factory ──────────────────────────────────────────────────────────────
# Uses create_agent with wrap_model_call middleware for dynamic model selection.
# Tools come only from app.tools.ALL_TOOLS (no separate tool service).

def _build_agent():
    """
    Build a LangChain agent via create_agent with dynamic model selection middleware.
    Basic model for short conversations; advanced (cloud) model when message count > threshold.
    Tools = ALL_TOOLS from app.tools. Returns None if no LLM is configured.
    This function is relatively expensive, so the resulting agent is cached at module level.
    """
    from app.services.llm_service import build_llm
    from langchain.agents import create_agent
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

    basic_model = build_llm(profile="default")
    if basic_model is None:
        return None

    advanced_model = build_llm(profile="advanced") or basic_model
    message_count_threshold = getattr(settings, "agent_advanced_message_threshold", 10)

    @wrap_model_call
    def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
        message_count = len(request.state.get("messages", []))
        if message_count > message_count_threshold:
            model = advanced_model
        else:
            model = basic_model
        return handler(request.override(model=model))

    system_prompt = _build_system_prompt(ALL_TOOLS)
    return create_agent(
        model=basic_model,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        middleware=[dynamic_model_selection],
    )


def _get_agent():
    """Return a cached agent instance to avoid rebuilding it on every request."""
    global _agent_cache
    if _agent_cache is not None:
        return _agent_cache
    agent = _build_agent()
    _agent_cache = agent
    return agent


# ── Public API ─────────────────────────────────────────────────────────────────

def invoke_agent(
    message: str,
    history: List[MessageItem],
    session_id: str = "",
    data_source: str | None = None,
) -> AgentResult:
    """
    Run the orchestrated ReAct agent on a user message.

    Falls back to a keyword-based demo response if no LLM is configured
    (preserves the existing demo-mode behaviour from the chat service).
    """
    bound_log = log.bind(session_id=session_id, preview=message[:60], data_source=data_source or "auto")
    bound_log.info("agent.invoke.start")
    start = time.perf_counter()

    agent = _get_agent()

    # ── Demo mode: no LLM configured ─────────────────────────────────────────
    if agent is None:
        bound_log.warning("agent.demo_mode")
        tool_names = [getattr(t, "name", str(t)) for t in ALL_TOOLS]
        return AgentResult(
            reply=(
                "[Demo mode — model URL not configured]\n"
                f"I would run the agent with all tools for: \"{message}\".\n"
                f"Available tools: {', '.join(tool_names)}."
            ),
            tool_steps=[],
            latency_ms=None,
            model=settings.effective_model_name,
            session_id=session_id,
        )

    # ── Build messages from history + new user message ────────────────────────
    # Use last N messages so in-memory session history correlates prompts (id-based)
    max_history = getattr(settings, "chat_memory_max_messages", 20)
    messages: List = []
    for item in history[-max_history:]:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=message))

    # ── Live agent invocation ─────────────────────────────────────────────────
    try:
        result = agent.invoke({"messages": messages})

        # Extract final reply, tool steps (with input args), token usage from state messages
        out_messages = result.get("messages", [])
        reply = "No response generated."
        tool_steps: List[ToolStep] = []
        tool_call_names: dict = {}  # tool_call_id -> tool name
        tool_call_args: dict = {}   # tool_call_id -> args dict

        def _tc_id(tc):
            if isinstance(tc, dict):
                return tc.get("id", "") or tc.get("tool_call_id", "")
            return getattr(tc, "id", "") or getattr(tc, "tool_call_id", "")

        def _tc_name(tc):
            if isinstance(tc, dict):
                return tc.get("name", "unknown")
            return getattr(tc, "name", "unknown")

        def _tc_args(tc):
            if isinstance(tc, dict):
                return tc.get("args", {}) or {}
            return getattr(tc, "args", {}) or {}

        # First pass: collect tool_call id -> name and id -> args from AIMessages
        for msg in out_messages:
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    call_id = _tc_id(tc)
                    if call_id:
                        tool_call_names[call_id] = _tc_name(tc)
                        tool_call_args[call_id] = _tc_args(tc)

        # Second pass: extract reply (last AI content) and tool steps from ToolMessages
        for msg in out_messages:
            if isinstance(msg, AIMessage):
                if msg.content:
                    if isinstance(msg.content, str):
                        reply = msg.content
                    elif isinstance(msg.content, list) and msg.content:
                        part = msg.content[0]
                        reply = part.get("text", str(part)) if isinstance(part, dict) else str(part)
            elif isinstance(msg, ToolMessage):
                tid = getattr(msg, "tool_call_id", "")
                name = tool_call_names.get(tid) or getattr(msg, "name", None) or "unknown"
                args = tool_call_args.get(tid, {})
                content = msg.content if isinstance(msg.content, str) else str(msg.content)[:500]
                tool_steps.append(ToolStep(tool=name, input=args, output=content))

        # Build reasoning steps for UI (thinking/reasoning display)
        reasoning_steps: List[str] = []
        for step in tool_steps:
            reasoning_steps.extend(_reasoning_lines_for_tool(step.tool, step.input))

        # Token usage: start from top-level usage (if provided) then
        # aggregate any per-message usage from AIMessage metadata.
        input_tokens_total: Optional[int] = None
        output_tokens_total: Optional[int] = None

        # Top-level usage (common with some providers / LangChain integrations)
        top_usage = result.get("usage")
        if isinstance(top_usage, dict):
            ni = (
                top_usage.get("input_tokens")
                or top_usage.get("prompt_tokens")
                or top_usage.get("total_prompt_tokens")
            )
            no = (
                top_usage.get("output_tokens")
                or top_usage.get("completion_tokens")
                or top_usage.get("total_completion_tokens")
            )
            if ni is not None:
                input_tokens_total = (input_tokens_total or 0) + int(ni)
            if no is not None:
                output_tokens_total = (output_tokens_total or 0) + int(no)

        # Per-message usage (each round may have usage)
        for msg in out_messages:
            if isinstance(msg, AIMessage):
                meta = getattr(msg, "response_metadata", None) or getattr(msg, "usage_metadata", None) or {}
                usage = meta.get("usage") if isinstance(meta.get("usage"), dict) else (meta if isinstance(meta, dict) else {})
                if isinstance(usage, dict):
                    ni = (
                        usage.get("input_tokens")
                        or usage.get("prompt_tokens")
                        or usage.get("total_prompt_tokens")
                    )
                    no = (
                        usage.get("output_tokens")
                        or usage.get("completion_tokens")
                        or usage.get("total_completion_tokens")
                    )
                    if ni is not None:
                        input_tokens_total = (input_tokens_total or 0) + int(ni)
                    if no is not None:
                        output_tokens_total = (output_tokens_total or 0) + int(no)
        # If the provider did not return usage metadata, approximate tokens
        # from character counts (simple heuristic: ~4 chars per token).
        def _approx_tokens_from_text(text: str) -> int:
            return max(1, int(len(text) / 4))

        if input_tokens_total is None:
            try:
                history_text = " ".join(
                    [h.content for h in history[-max_history:]]  # type: ignore[attr-defined]
                )
            except Exception:
                history_text = ""
            approx_in = _approx_tokens_from_text(history_text + " " + message)
            input_tokens_total = approx_in

        if output_tokens_total is None:
            approx_out = _approx_tokens_from_text(str(reply))
            output_tokens_total = approx_out

        input_tokens = input_tokens_total
        output_tokens = output_tokens_total

        if tool_steps:
            bound_log.info("agent.tool_steps", tools=[s.tool for s in tool_steps])

        latency_ms = int((time.perf_counter() - start) * 1000)
        bound_log.info("agent.invoke.done", latency_ms=latency_ms, tool_steps=len(tool_steps))

        return AgentResult(
            reply=reply,
            tool_steps=tool_steps,
            reasoning_steps=reasoning_steps,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=settings.effective_model_name,
            session_id=session_id,
        )

    except Exception as exc:
        bound_log.exception("agent.invoke.error", error=str(exc))
        raise
