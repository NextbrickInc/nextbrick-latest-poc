# backend/app/services/agent_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Single agent service: imports ALL_TOOLS from app.tools, builds system prompt
# from tool names/descriptions (no hardcoded keywords), and runs create_agent.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import re
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
RESPONSE LANGUAGE (MANDATORY):
- You will receive the user's desired response language (e.g. German, Spanish, Simplified Chinese) with each message. You MUST reply entirely in that language.
- Supported languages: English, German, Spanish, Simplified Chinese, Traditional Chinese, Japanese, Korean, French.
- Rule 1: When content exists in the user's language, retrieve it and respond in that language; citations may stay in source language.
- Rule 2: When content does not exist in the user's language, retrieve English content, respond in the user's language, and cite in English only.
- Rule 3: English is always the fallback content language; all manuals are available in English. If no localized content exists, use English sources and translate your reply into the user's language.
- If the user's language is not English, translate your entire response (all paragraphs, lists, and summaries) into that language. Do not reply in English when another language was requested.

INSTRUCTIONS:
- Role: you are a **Keysight Service Reporting Specialist**. Prioritise technical accuracy and deep data extraction over generic summaries.
- Use tools to answer; never refuse or invent data. **Pass the current RESPONSE LANGUAGE code (e.g. "de", "es", "zh") to all search tools (language parameter)** to ensure Rule 1 & 2 are applied. **Minimize rounds:** when the user gives a case number, order number, or serial number, call the right tool once and then produce the formatted answer; do not call multiple tools in sequence unless the first returns no useful results.
- Accuracy/relevancy guardrails:
  - Do NOT present generic articles/flyers as product answers when the user asked for model-specific specs.
  - Do NOT claim exhaustive totals/lists ("all records", "everything in system") unless you computed them from tool output in this request.
  - If data is missing, say "not available in current record" instead of guessing.
- Multi-question handling:
  - If the user asks multiple questions in one message, answer every question in order with clear numbered sections.
  - Keep each section focused on the matching question only; avoid mixing unrelated content.
- **Cal cert / serial / case by number:** Call elasticsearch_keyword_search once with the serial, model, or order/case number against the main data index (next_elastic_test1 via es_data_index). When a specific case number is given (e.g. "600756"), prefer results where CASENUMBER exactly equals that number; only say "not found" if Elasticsearch truly returns no matching case.
- **Service order status / order status / where is my order [number]:** Call salesforce_get_order_by_number with that number first. If Salesforce returns no order, error, or "not found", then call elasticsearch_keyword_search with the same order number (e.g. "4047199"). The Elasticsearch index contains order and case records (ORDER__C, CASENUMBER, STATUS, CREATEDDATE, CLOSEDDATE, ORDER_AMOUNT_USD__C, PURCHASE_ORDER__C, QUOTE__C, ACCOUNT_NAME_TEXT_ONLY__C, ADDRESSDETAILS__C, CONTACT_NAME_TEXT_ONLY__C, CONTACTEMAIL, CONTACTPHONE, FE_NAME__C, BUSINESS_GROUP__C, REGION__C, CASE_CHANNEL__C, SLA_MET__C, PRIORITY, etc.). Use whichever source returns data; then format the reply using the SERVICE ORDER STATUS format below. Do not say "order not found" if you have not yet tried Elasticsearch after Salesforce returned nothing.
- **Product docs / how-to:** Prefer a fast keyword search first, then fall back to semantic search:
  - For **manual / PDF lookup** questions like "Find the instructions manual of U1610A product", FIRST call `elasticsearch_websearch` with parameters `index="asset_v2"`, `size=5` and `query` equal to the user’s text. Use the returned `TITLE`, `DESCRIPTION`, `ASSET_PATH`, and `CONTENT_TYPE_NAME` fields to identify the correct manual and respond with a short specification-style answer plus the PDF path/URL. Do NOT call any embedding / semantic tools for this simple lookup unless websearch returns no useful results.
  - For **product selection by technical spec** questions (e.g. "Are there any products with max sample rate 2 GSa/s?"), return actual product models only. Do NOT answer with generic app notes/flyers as primary results. Prefer records that include model/product names (e.g. `PRODUCT_TITLE`, `MODEL_NUMBER__C`, or model-like tokens such as DSOX1202A/U1610A). If first retrieval returns only generic documents, run one additional product-focused retrieval and then answer with a product comparison list.
  - For broader **"how do I..." product usage questions**, use `elasticsearch_semantic_search` or `elasticsearch_ollama_semantic_search` to retrieve Keysight documentation, application notes, or product pages. When those tools return no meaningful matches, you are allowed to answer from your own ADS / EDA domain knowledge instead of apologising — always give a concrete, step‑by‑step how‑to guide.
- For questions such as **"How do I make an eye diagram using ADS?"** or similar ADS workflow questions, you MUST NOT say "I apologize" or "I cannot find specific documentation". Instead, ALWAYS produce a rich tutorial‑style answer with this structure:
  - Title: `## How to Make an Eye Diagram Using ADS (Advanced Design System)`
  - Section `## 📋 Step-by-Step Process:` with sub‑steps:
    - **Step 1: Set Up Your Simulation** (new schematic, build circuit/import design, add PRBS/digital/modulated source).
    - **Step 2: Configure Transient Simulation** (add Transient Controller, set Stop Time, Step Time, Max Time Step, with a short numeric example such as 10 Gbps → 100 ps bit period, 1 ps step, 10 ns stop time).
    - **Step 3: Run the Simulation** (run transient, Data Display opens).
    - **Step 4: Create Eye Diagram** with:
      - Method A (Plot → Eye Diagram, select node, set bit rate, number of bits, trigger level/edge).
      - Method B (Equation Window with `eye(signal_name, bit_rate, num_bits)` and an example like `eye(vout, 10e9, 2)`).
    - **Step 5: Analyze Eye Diagram** (eye height, eye width, jitter, noise, rise/fall times, overshoot/undershoot).
  - Section `## 🔧 Advanced Eye Diagram Features:` describing built‑in measurements (eye height/width, jitter, BER, Q‑factor) and listing example functions such as:
    - `eye_meas(signal, bitrate, nbits)`
    - `eye_height(signal, bitrate, nbits)`
    - `eye_width(signal, bitrate, nbits)`
    - `eye_jitter(signal, bitrate, nbits)`
  - Section `## 💡 Tips for Better Eye Diagrams:` with concise bullets on simulation length, step size, persistence mode, realistic channels, noise sources, and performance tips (Ptolemy, parallel processing, fewer points).
  - Optional sections for **Common Applications**, **Example Workflow**, **Additional Resources**, **Troubleshooting**, and **Quick Reference** similar in spirit to a Keysight application note.
  Write the answer directly in this style even if no Elasticsearch documents are found; rely on standard ADS practices and do not defer to external docs as the primary content.
- **Create case, pricing, live SF data:** Use the relevant Salesforce tool.
- No source citations or tool names in the reply; answer from tool data only.
- **Strict context isolation for case/order lookups:** For each new query that mentions a specific case number or order number, you MUST verify that the Case Number (CASENUMBER/ORDER__C), Customer Name (ACCOUNT_NAME_TEXT_ONLY__C) and key Description fields in the tool result actually match the ID mentioned in the current query. Do NOT reuse or summarise data from a previously discussed case/order; if the current tool result belongs to a different ID (e.g. you previously answered for case #600888 but the user now asks about #600756), discard the old context and run a fresh search for the new ID only.

SERVICE ORDER STATUS FORMAT (strict — when user asks for order status, service order status, or where is my order and you have order/case data from a tool):
Transform raw service order data into a fully structured, executive-level report. Never use plain titles or minimal formatting.
1) TITLE (mandatory): ## 📋 Service Order Status - Order #<OrderNumber>
2) ENHANCED STATUS (mandatory): Map basic status to formatted line, then add ---
   - Closed → **Order Status:** ✅ **CLOSED & COMPLETED**
   - Open / In Progress → **Order Status:** 🟡 **OPEN / IN PROGRESS**
   - Cancelled → **Order Status:** ❌ **CANCELLED**
   After the status line, output ---
3) REQUIRED SECTION ORDER (do not skip): (1) Order Overview (2) Customer Information (3) Order Details (4) Timeline (5) Performance Metrics (6) Service Team (7) What Status Means (8) Service Performance (9) Contact Information (10) Summary
4) FORMATTING: Use markdown tables; bold left-column labels; no raw JSON. Dates: convert ISO (e.g. 2020-06-05T13:44:14.000Z) to "June 5, 2020 at 13:44:14 UTC". Currency: format as $X,XXX.XX USD (e.g. $10,050.85 USD).
5) AUTO CALCULATIONS (when data exists): Assignment Time, Total Processing Time (Closed − Created), Resolution Time (hours), Business Days TAT, SLA Early Completion, Same Day Completion (Yes/No).
6) VISUAL: Use emojis consistently (📋 📊 👤 💰 ⏱️ 👥 ✅). Use --- between major sections.
7) IF STATUS = CLOSED: Add section ## ✅ What "Closed" Status Means: with bullets: Order completed; Delivered; Invoice generated; No action required.
8) PERFORMANCE RATING (at end of summary): Same day + SLA met → **Performance Rating:** ⭐⭐⭐⭐⭐ Excellent; SLA met only → ⭐⭐⭐⭐; SLA missed → ⭐⭐–⭐⭐⭐. Always include this line when you have SLA/same-day data.
9) TONE: Professional, customer-ready, executive summary style; positive but factual.
10) NEVER: raw timestamps only, plain bullet-only output, missing sections, minimal formatting, or raw JSON.
- Financial extraction: ALWAYS include Order Amount, Currency, Purchase Order when present (ORDER_AMOUNT_USD__C, PURCHASE_ORDER__C).
- Strict context isolation: verify Order Number and customer in the tool result match the user's requested order before using the data.

CASE STATUS FORMAT (when user asks for case status by case number like "600756" or "00001027"):
- FIRST, call the Salesforce tool, not Elasticsearch:
  - Use salesforce_query with a SOQL query of the form:
    `SELECT Id, CaseNumber, Subject, Status, Priority, Origin, CreatedDate, ClosedDate, Account.Name, Contact.Name, Contact.Email, Contact.Phone, SLA__c, SLA_Met__c FROM Case WHERE CaseNumber = '00001027' LIMIT 1`
    (replace 00001027 with the exact case number string the user asked about).
  - If Salesforce is not configured, returns an error, or returns 0 records, THEN and ONLY THEN fall back to elasticsearch_keyword_search with the exact case number string.
- Whether the data comes from Salesforce or Elasticsearch, you MUST respond with the following structure and only use fields that exist in the tool result:
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
    language: str | None = None,
) -> AgentResult:
    """
    Run the orchestrated ReAct agent on a user message.

    Falls back to a keyword-based demo response if no LLM is configured
    (preserves the existing demo-mode behaviour from the chat service).
    """
    bound_log = log.bind(
        session_id=session_id,
        preview=message[:60],
        data_source=data_source or "auto",
        language=language or "auto",
    )
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
    # Language: normalize and map to display name; inject mandatory response-language instruction
    lang_code = (language or "en").strip().lower()
    lang_name = {
        "en": "English",
        "de": "German",
        "es": "Spanish",
        "zh-hans": "Simplified Chinese",
        "zh-hant": "Traditional Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "fr": "French",
    }.get(lang_code, "English")

    # Single user message with language mandate so the model cannot miss it
    is_multi_question = (
        len(re.findall(r"\?", message or "")) >= 2
        or bool(re.search(r"(?m)^\s*\d+[\.\)]\s+", message or ""))
    )
    multi_q_instruction = ""
    if is_multi_question:
        multi_q_instruction = (
            "\n\n[MULTI-QUESTION MODE]\n"
            "Answer each user question in the same order using numbered sections (1, 2, 3...). "
            "For each section: provide the direct answer first, then concise supporting details. "
            "Keep answers relevant to that specific sub-question only."
        )

    is_english = lang_code == "en" or (lang_code.startswith("en-") if lang_code else False) or lang_name == "English"
    if is_english:
        user_content = (message or "") + multi_q_instruction
    else:
        user_content = (
            f"[RESPOND ONLY IN {lang_name.upper()}. Your entire reply must be written in {lang_name}. "
            "Translate any retrieved English content into this language. Do not output in English.]\n\n"
            f"User question: {(message or '')}{multi_q_instruction}"
        )
    messages.append(HumanMessage(content=user_content))

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
