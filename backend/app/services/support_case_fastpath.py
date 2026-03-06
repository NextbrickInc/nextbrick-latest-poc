from __future__ import annotations

import re
from typing import Optional, Tuple, List


_INTENT_PATTERNS = [
    re.compile(r"\bcreate\b.*\bsupport\s*case\b", re.I),
    re.compile(r"\bcreate\b.*\bcase\b", re.I),
    re.compile(r"\bopen\b.*\bsupport\s*case\b", re.I),
]


def _is_create_case_intent(text: str) -> bool:
    q = (text or "").strip()
    if not q:
        return False
    return any(p.search(q) for p in _INTENT_PATTERNS)


def _extract_field(text: str, field_name: str) -> str:
    # Supports: subject: ..., description: ..., product details: ...
    # Stops when the next known field starts.
    pattern = re.compile(
        rf"\b{field_name}\b\s*[:=]\s*(.+?)(?=\b(?:subject|description|product\s*details?|priority)\b\s*[:=]|$)",
        re.I | re.S,
    )
    m = pattern.search(text or "")
    if not m:
        return ""
    return m.group(1).strip(" \n\t-+")


def try_support_case_fastpath(message: str, language: Optional[str] = None) -> Optional[Tuple[str, List[str]]]:
    """
    Fast-path for support-case creation:
    - If required fields are missing -> instant guidance (no LLM/tool loop).
    - If fields provided -> one direct Salesforce create call (no agent loop).
    """
    msg = (message or "").strip()
    if not _is_create_case_intent(msg):
        return None

    subject = _extract_field(msg, "subject")
    description = _extract_field(msg, "description")
    product_details = _extract_field(msg, r"product\s*details?")
    priority = _extract_field(msg, "priority") or "Medium"

    # Missing required fields -> instant structured prompt
    if not subject or not description:
        reply = (
            "## Create Support Case\n\n"
            "Please provide the required fields in one message:\n\n"
            "- `subject: <short title>`\n"
            "- `description: <issue details>`\n"
            "- `product details: <model/serial/version>` (recommended)\n"
            "- `priority: Low|Medium|High|Critical` (optional)\n\n"
            "Example:\n"
            "`Create Support Case using subject: Scope not booting; description: Unit fails at startup with error code E12; product details: DSOX1202A SN MY12345678 FW 1.2.3; priority: High`"
        )
        return (reply, ["support_case_fastpath"])

    final_description = description
    if product_details:
        final_description = f"{description}\n\nProduct Details:\n{product_details}"

    try:
        from app.tools.salesforce_tool import salesforce_create_case

        out = salesforce_create_case.invoke(
            {"subject": subject, "description": final_description, "priority": priority}
        )
    except Exception as e:
        return (
            f"## Create Support Case\n\nCase creation failed due to a backend error: {e}",
            ["support_case_fastpath"],
        )

    if isinstance(out, dict) and out.get("success") and out.get("id"):
        case_id = out.get("id")
        reply = (
            "## Support Case Created\n\n"
            f"✅ Your support case was created successfully.\n\n"
            f"- **Case ID:** `{case_id}`\n"
            f"- **Subject:** {subject}\n"
            f"- **Priority:** {priority}\n\n"
            "You can now ask: `give me case status <case number>` once the CaseNumber is available."
        )
        return (reply, ["salesforce_create_case"])

    # Tool returned structured error
    if isinstance(out, dict) and out.get("message"):
        return (f"## Create Support Case\n\n{out.get('message')}", ["salesforce_create_case"])

    return ("## Create Support Case\n\nUnable to create case right now. Please try again.", ["salesforce_create_case"])

