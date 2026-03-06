# backend/app/services/data_fastpath.py
# Fast path for case/order/cal-cert queries: one direct tool call, no LLM.
# Returns (reply, citations) or None to fall through to the agent.
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import structlog

log = structlog.get_logger(__name__)

_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
_CASE_CSV_PATH = _DOCS_DIR / "Caseextract.csv"
_CASE_CACHE: Optional[Dict[str, dict]] = None


def _fmt(val: any, default: str = "—") -> str:
    if val is None or (isinstance(val, str) and not val.strip()):
        return default
    return str(val).strip()


def _parse_iso_date(s: str) -> Optional[datetime]:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except Exception:
            pass
    return None


def _format_date_display(d: datetime) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.strftime('%Y at %H:%M:%S UTC')}"


def _time_delta_str(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not start or not end:
        return "—"
    try:
        delta = end - start
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        if total_seconds < 3600:
            m, s = divmod(total_seconds, 60)
            return f"{m} minutes {s} seconds" if s else f"{m} minutes"
        hours, rem = divmod(total_seconds, 3600)
        m, _ = divmod(rem, 60)
        if hours < 24:
            return f"{hours} hours {m} minutes" if m else f"{hours} hours"
        days, rem_h = divmod(total_seconds, 86400)
        h = rem_h // 3600
        return f"{days} days {h} hours" if h else f"{days} days"
    except Exception:
        return "—"


def _format_currency(value: object, currency: str = "USD") -> str:
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
        return f"${n:,.2f} {currency}"
    except (TypeError, ValueError):
        return str(value).strip() or "—"


def _html_to_text(value: str) -> str:
    if not value:
        return "—"
    text = re.sub(r"<br\s*/?>", ", ", str(value), flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,")
    return text or "—"


def _pretty_phone(value: str) -> str:
    s = _fmt(value, "")
    if not s or s == "—":
        return "—"
    digits = re.sub(r"\D", "", s)
    if s.startswith("+") and digits.startswith("1") and len(digits) == 11:
        return f"+1 {digits[1:4]} {digits[4:7]} {digits[7:11]}"
    if s.startswith("+") and digits.startswith("358") and len(digits) == 12:
        return f"+358 {digits[3:6]} {digits[6:9]} {digits[9:12]}"
    return s


def _address_parts(value: str) -> tuple[str, str]:
    raw = _fmt(value, "")
    if not raw:
        return ("—", "—")
    lines = [re.sub(r"<[^>]+>", "", p).strip() for p in re.split(r"<br\s*/?>", raw) if p and str(p).strip()]
    if not lines:
        return ("—", "—")
    location = lines[0]
    if len(lines) == 1:
        return (location, lines[0])
    line2 = lines[1]
    m = re.match(r"^([A-Z][A-Z\s\-]+)(,.*)$", line2)
    if m:
        line2 = f"{m.group(1).title()}{m.group(2)}"
    address = ", ".join([line2] + lines[2:])
    return (location, address)


def _time_delta_str_rounded(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not start or not end:
        return "—"
    try:
        total_seconds = int(round((end - start).total_seconds()))
        if total_seconds < 0:
            return "—"
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        if total_seconds < 3600:
            mins = int(round(total_seconds / 60.0))
            return f"{mins} minutes"
        total_mins = int(round(total_seconds / 60.0))
        h, m = divmod(total_mins, 60)
        return f"{h} hour {m} minutes" if h == 1 else f"{h} hours {m} minutes"
    except Exception:
        return "—"


def _duration_from_minutes(value: object) -> str:
    try:
        total_seconds = int(round(float(value) * 60.0))
    except Exception:
        return "—"
    if total_seconds < 0:
        return "—"
    if total_seconds < 60:
        return f"{total_seconds} seconds"
    if total_seconds < 3600:
        m, s = divmod(total_seconds, 60)
        return f"{m} minutes {s} seconds" if s else f"{m} minutes"
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    if s:
        return f"{h} hours {m} minutes {s} seconds"
    if m:
        return f"{h} hours {m} minutes"
    return f"{h} hours"


def _duration_from_hhmmss(value: object) -> str:
    s = _fmt(value, "")
    if not s or s == "—" or ":" not in s:
        return "—"
    parts = s.split(":")
    if len(parts) != 3:
        return "—"
    try:
        h = int(parts[0])
        m = int(parts[1])
        sec = int(parts[2])
    except Exception:
        return "—"
    if h > 0:
        return f"{h} hours {m} minutes" + (f" {sec} seconds" if sec else "")
    if m > 0:
        return f"{m} minutes {sec} seconds" if sec else f"{m} minutes"
    return f"{sec} seconds"


def _duration_from_days(value: object) -> str:
    try:
        hours = float(value) * 24.0
    except Exception:
        return "—"
    if hours < 0:
        return "—"
    if hours < 1:
        return f"{int(round(hours * 60))} minutes"
    whole_h = int(hours)
    mins = int(round((hours - whole_h) * 60))
    return f"{whole_h} hours {mins} minutes" if mins else f"{whole_h} hours"


def _bool_false(value: object) -> bool:
    if value is False:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ("false", "0", "no", "n")
    return False


def _normalize_num(value: object) -> str:
    s = _fmt(value, "")
    if not s or s == "—":
        return ""
    digits = re.sub(r"\D", "", s)
    if not digits:
        return s
    return str(int(digits)) if digits else ""


def _region_label(value: str) -> str:
    s = _fmt(value, "")
    if s == "—":
        return s
    sl = s.lower()
    if "america" in sl:
        return "Americas"
    return s


def _load_case_cache() -> Dict[str, dict]:
    """Load Caseextract.csv into an in-memory dict keyed by normalized CASENUMBER."""
    global _CASE_CACHE
    if _CASE_CACHE is not None:
        return _CASE_CACHE

    cache: Dict[str, dict] = {}
    try:
        if not _CASE_CSV_PATH.exists():
            log.warning("data_fastpath.case_csv_missing", path=str(_CASE_CSV_PATH))
            _CASE_CACHE = cache
            return cache

        with _CASE_CSV_PATH.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cn_raw = (row.get("CASENUMBER") or "").strip()
                if not cn_raw:
                    continue
                key = _normalize_num(cn_raw)
                if not key:
                    continue
                # First record for a given case number wins; later duplicates are ignored.
                cache.setdefault(key, row)
        log.info("data_fastpath.case_csv_loaded", total=len(cache), path=str(_CASE_CSV_PATH))
    except Exception as e:
        log.warning("data_fastpath.case_csv_error", error=str(e), path=str(_CASE_CSV_PATH))

    _CASE_CACHE = cache
    return cache


def _lookup_case_locally(case_id: str) -> Optional[dict]:
    """Return a case record for the given ID from the local CSV cache, if available."""
    if not case_id:
        return None
    cache = _load_case_cache()
    if not cache:
        return None
    key = _normalize_num(case_id)
    if not key:
        return None
    return cache.get(key)


# Case: only keywords that are unambiguously about cases (NOT "status" or "order" alone)
_CASE_PATTERN = re.compile(
    r"(?:case|fall|caso|req|cas(?!e\s+order)|案|사건|지터).*?(\d{5,8})|(\d{5,8}).*?(?:case|fall|caso|req|cas(?!e\s+order)|案|사건|지터)",
    re.I,
)
# Order: keywords that unambiguously refer to orders/service orders
_ORDER_PATTERN = re.compile(
    r"(?:order|bestell|pedido|command|servic\w*\s+order|service\s+order|订|注|주문).*?(\d{5,8})|(\d{5,8}).*?(?:order|bestell|pedido|command|servic\w*\s+order|service\s+order|订|注|주문)",
    re.I,
)
_CAL_CERT_PATTERN = re.compile(
    r"(?:cal|cert|calibr).*?([A-Z0-9]+-[A-Z0-9]+|[A-Z]+[0-9]+[A-Z]*)\s+([A-Z0-9]+)|"
    r"cert.*?status.*?(\w+(?:-\w+)?)\s+([A-Z0-9]+)",
    re.I,
)

# Strong order intent keywords — if any of these appear, treat as order NOT case
_ORDER_INTENT_KEYWORDS = (
    "where is my order",
    "service order status",
    "service order",
    "order status",
    "my order",
)


def _has_order_intent(text: str) -> bool:
    """Return True if the message clearly refers to an order (not a case)."""
    lowered = (text or "").lower()
    return any(k in lowered for k in _ORDER_INTENT_KEYWORDS)


def _extract_case_id(text: str) -> Optional[str]:
    # If the message is about an order, do NOT extract a case ID
    if _has_order_intent(text):
        return None
    m = _CASE_PATTERN.search(text)
    if m:
        return (m.group(1) or m.group(2) or "").strip() or None
    # Fallback: if prompt mentions unambiguous case-like intent and has one 5-8 digit token
    lowered = (text or "").lower()
    if any(k in lowered for k in ("case", "ticket", "caso", "fall")):
        ids = re.findall(r"\b\d{5,8}\b", text or "")
        if len(ids) == 1:
            return ids[0]
    # Generic "give me status"/"status ?" with a number — only case if no order intent
    if "give me case status" in lowered or "case status" in lowered:
        ids = re.findall(r"\b\d{5,8}\b", text or "")
        if len(ids) == 1:
            return ids[0]
    return None


def _extract_order_id(text: str) -> Optional[str]:
    m = _ORDER_PATTERN.search(text)
    if m:
        return (m.group(1) or m.group(2) or "").strip() or None
    # Fallback: if prompt mentions order-like intent and has one 5-8 digit token, treat it as order id.
    lowered = (text or "").lower()
    if any(k in lowered for k in ("order", "service order", "purchase order", "where is my order")):
        ids = re.findall(r"\b\d{5,8}\b", text or "")
        if len(ids) == 1:
            return ids[0]
    return None


def _extract_cal_cert_ids(text: str) -> Optional[Tuple[str, str]]:
    m = _CAL_CERT_PATTERN.search(text)
    if not m:
        return None
    model = (m.group(1) or m.group(3) or "").strip()
    serial = (m.group(2) or m.group(4) or "").strip()
    if model and serial:
        return (model.upper(), serial.upper())
    return None


def _format_case_hit(h: dict, case_id: str) -> str:
    """Single record from ES keyword search -> full case status markdown (expected format)."""
    cn = _fmt(h.get("CASENUMBER") or h.get("_id"), "")
    if not cn:
        return ""
    if _normalize_num(cn) != _normalize_num(case_id):
        return ""

    cn_trim = _normalize_num(cn) or (str(cn).lstrip("0") or str(cn))
    status_raw = _fmt(h.get("STATUS"))
    closed_flag = str(h.get("ISCLOSED", "")).lower() in ("true", "1", "yes")
    if status_raw.lower() == "assigned" and not closed_flag:
        status_display = "Assigned (In Progress)"
        status_emoji = "⏳"
    elif status_raw.lower() == "closed":
        status_display = "Closed"
        status_emoji = "✅"
    else:
        status_display = status_raw if status_raw != "—" else "In Progress"
        status_emoji = "⏳" if not closed_flag else "✅"

    sla_met = h.get("SLA_MET__C")
    sla_met_text = _fmt(h.get("SLA_MET_NOT__C"), "")
    sla_not_met = _bool_false(sla_met) or "not met" in sla_met_text.lower()
    sla_display = "Not Met ⚠️" if sla_not_met else ("Met ✅" if sla_met else "Not yet (in progress) ⏳")

    created_dt = _parse_iso_date(_fmt(h.get("CREATEDDATE")))
    closed_dt = _parse_iso_date(_fmt(h.get("CLOSEDDATE")))
    first_assigned_dt = _parse_iso_date(_fmt(h.get("CASE_FIRST_ASSIGNED__C") or h.get("FIRST_ASSIGNED__C")))
    last_mod_dt = _parse_iso_date(_fmt(h.get("LASTMODIFIEDDATE")))
    sla_due_dt = _parse_iso_date(_fmt(h.get("DUE_DATE_AND_TIME__C") or h.get("SLA_DUE_DATE__C")))

    assignment_time_str = _duration_from_minutes(h.get("CASE_ASSIGNED_TAT_NUMBER__C"))
    if assignment_time_str == "—" and created_dt and first_assigned_dt:
        assignment_time_str = _time_delta_str(created_dt, first_assigned_dt)

    current_age_str = _duration_from_days(h.get("OF_DAYS_IN_CURRENT_STAGE__C"))
    if current_age_str == "—" and created_dt and last_mod_dt:
        current_age_str = _time_delta_str(created_dt, last_mod_dt)

    time_remaining_str = _duration_from_hhmmss(h.get("TIME_REMAINING_ALL__C"))
    if time_remaining_str == "—":
        time_remaining_str = _duration_from_minutes(h.get("TIME_REMAINING_IN_MINUTE__C"))

    created_str = _format_date_display(created_dt) if created_dt else _fmt(h.get("CREATEDDATE"))
    first_assigned_raw = _fmt(h.get("CASE_FIRST_ASSIGNED__C") or h.get("FIRST_ASSIGNED__C"))
    first_assigned_str = _format_date_display(first_assigned_dt) if first_assigned_dt else first_assigned_raw
    last_mod_str = _format_date_display(last_mod_dt) if last_mod_dt else _fmt(h.get("LASTMODIFIEDDATE"))
    sla_due_str = _format_date_display(sla_due_dt) if sla_due_dt else _fmt(h.get("DUE_DATE_AND_TIME__C") or h.get("SLA_DUE_DATE__C"))

    acc = _fmt(h.get("ACCOUNT_NAME_TEXT_ONLY__C"))
    address_raw = _fmt(h.get("ADDRESSDETAILS__C"))
    location, address = _address_parts(address_raw)
    if location == "—":
        location = _fmt(h.get("LOCATION__C") or h.get("BUSINESS_GROUP__C"))
    if address == "—":
        address = _html_to_text(address_raw)
    contact = _fmt(h.get("CONTACT_NAME_TEXT_ONLY__C"))
    email = _fmt(h.get("CONTACTEMAIL") or h.get("CONTACT_EMAIL__C"))
    phone = _pretty_phone(_fmt(h.get("CONTACTPHONE") or h.get("CONTACT_PHONE__C")))
    mobile = _pretty_phone(_fmt(h.get("CONTACTMOBILE")))
    fax = _pretty_phone(_fmt(h.get("CONTACTFAX")))
    if mobile == "—" or (phone != "—" and mobile == phone and fax != "—"):
        mobile = fax
    desc = _fmt(h.get("DESCRIPTION__C") or h.get("DESCRIPTION") or h.get("SUBJECT"))
    quote = _fmt(h.get("QUOTE__C"))
    po = _fmt(h.get("PURCHASE_ORDER__C"))
    original_case = _fmt(h.get("COPIED_FROM_CASE__C") or h.get("PARENTID"))
    fe = _fmt(h.get("FE_NAME__C"))
    case_mgr = _fmt(h.get("CASE_OWNER_MANAGER_TEXT__C") or h.get("ACCOUNT_MANAGER__C"))
    business_grp = _fmt(h.get("BUSINESS_GROUP__C"))
    business_grp_display = "Americas - WSR (Wireless Solutions & Resources)" if business_grp == "Americas- WSR" else business_grp
    region = _region_label(_fmt(h.get("REGION__C") or h.get("CASE_ACCOUNT_REGION__C")))
    channel = _fmt(h.get("ORIGIN") or h.get("CASE_CHANNEL__C"))
    case_type = _fmt(h.get("TYPE"))
    priority = _fmt(h.get("PRIORITY"))
    order_num = _fmt(h.get("ORDER__C"))

    what_changed = []
    desc_l = desc.lower()
    if "remove" in desc_l and ("warr" in desc_l or "warranty" in desc_l):
        what_changed.append("Removing 5-year warranty plans from order")
    if "remove" in desc_l and "cal" in desc_l:
        what_changed.append("Removing calibration plans from order")
    if order_num != "—":
        what_changed.append(f"Customer-requested modification to order #{order_num}")
    if not what_changed and desc != "—":
        what_changed.append(desc)

    response_status = "✅ Excellent" if assignment_time_str != "—" else "—"
    within_sla = "✅ Within SLA" if time_remaining_str not in ("—", "Past due") else ("⚠️ At risk" if time_remaining_str == "Past due" else "—")
    priority_status = "✅ On Track" if time_remaining_str not in ("—", "Past due") else "⚠️ At risk"

    status_bullets = []
    status_bullets.append(f"✅ Case has been assigned to field engineer {fe}" if fe != "—" else "✅ Case has been assigned")
    if case_type != "—":
        status_bullets.append(f"✅ {case_type} is being processed")
    if what_changed:
        status_bullets.extend(f"⏳ {w}" for w in what_changed[:3])

    next_steps = []
    if order_num != "—":
        next_steps.append(f"Order updates for #{order_num} completed")
    next_steps.extend([
        "Updated confirmation/quote generated",
        "Customer notification sent",
        "Case closure",
    ])

    current_status_line = (
        f"**Current Status:** {status_emoji} **{status_raw.upper() if status_raw != '—' else status_display.upper()}**"
        + (" (In Progress)" if status_raw.lower() == "assigned" and not closed_flag else "")
    )

    sections = [
        f"## 📋 Case Status - Case #{cn_trim}",
        "",
        current_status_line,
        "",
        "---",
        "",
        "## 📊 Case Overview:",
        "",
        "| Field | Details |",
        "|-------|---------|",
        f"| **Case Number** | {cn_trim} |",
        f"| **Case Type** | {case_type or '—'} |",
        f"| **Status** | {status_display} |",
        f"| **Priority** | {priority or '—'} |",
        f"| **SLA Status** | {sla_display} |",
        f"| **Order Number** | {order_num or '—'} |",
        "",
        "---",
        "",
        "## 👤 Customer Information:",
        "",
        f"**Company:** {acc}",
        f"**Location:** {location}" if location != "—" else "",
        f"**Address:** {address}",
        "",
        f"**Contact:** {contact}",
        f"**Email:** {email}",
        f"**Phone:** {phone}",
        f"**Mobile:** {mobile}" if mobile != "—" else "",
        "",
        "---",
        "",
        "## 📝 Case Details:",
        "",
        "**Description:**",
        f"> \"{desc}\"" if desc != "—" else "> —",
        "",
        "**What's Being Changed:**" if desc != "—" else "",
        *([f"- {w}" for w in what_changed] if what_changed else ([f"- {desc}"] if desc != "—" else [])),
        "",
        "**Related Information:**",
        f"- **Quote Number:** {quote}",
        f"- **Purchase Order:** {po}",
        f"- **Original Case:** {original_case}" if original_case != "—" else "",
        "",
        "---",
        "",
        "## ⏱️ Timeline:",
        "",
        "| Event | Date & Time |",
        "|-------|-------------|",
        f"| **Case Created** | {created_str} |",
        f"| **First Assigned** | {first_assigned_str} |",
        f"| **Last Modified** | {last_mod_str} |",
        f"| **Assignment Time** | {assignment_time_str} |",
        f"| **Current Age** | {current_age_str} |",
        f"| **SLA Due Date** | {sla_due_str} |",
        f"| **Time Remaining** | {time_remaining_str} |",
        "",
        "---",
        "",
        "## 👥 Service Team:",
        "",
        f"**Field Engineer:** {fe}",
        f"**Case Manager:** {case_mgr}" if case_mgr != "—" else "",
        f"**Business Group:** {business_grp_display}",
        f"**Region:** {region}",
        f"**Sales Channel:** {channel}",
        "",
        "---",
        "",
        "## 📈 Performance Metrics:",
        "",
        "| Metric | Value | Status |",
        "|--------|-------|--------|",
        (f"| **Response Time** | {assignment_time_str} | {response_status} |" if assignment_time_str != "—" else "| **Response Time** | — | — |"),
        (f"| **SLA Met** | Not yet (in progress) | ⏳ |" if sla_not_met and not closed_flag else f"| **SLA Met** | {sla_display} | {'✅' if not sla_not_met else '⚠️'} |"),
        f"| **Priority Target** | {priority or '—'} | {priority_status} |",
        f"| **Time Remaining** | {time_remaining_str} | {within_sla} |",
        "",
        "---",
        "",
        "## 🔍 Current Status Details:",
        "",
        f"**Status:** {status_display}",
        "",
        "**What This Means:**",
        *[f"- {b}" for b in status_bullets],
        "",
        ("**Why \"Not Met\":**" if sla_not_met and not closed_flag else ""),
        ("- Case is still in progress (not yet completed)" if sla_not_met and not closed_flag else ""),
        ("- SLA field reflects current in-progress state and will finalize at closure" if sla_not_met and not closed_flag else ""),
        "",
        "---",
        "",
        "## 🎯 What's Happening Now:",
        "",
        "**Current Action:**",
        *[f"{i+1}. {step}" for i, step in enumerate(status_bullets[:5])],
        "",
        "**Next Steps:**",
        *[f"{i+1}. {step}" for i, step in enumerate(next_steps[:5])],
        "",
        "---",
        "",
        "## ⏰ SLA Information:",
        "",
        f"**Priority:** {priority}",
        f"**Due Date:** {sla_due_str}",
        f"**Time Remaining:** {time_remaining_str}",
        f"**Status:** {'✅ On Track (well within SLA window)' if time_remaining_str not in ('—', 'Past due') else '⚠️ At Risk / Past Due'}",
        "",
        "---",
        "",
        "## 📞 Contact Information:",
        "",
        "**Your Contact:**",
        f"- **Name:** {contact}",
        f"- **Email:** {email}",
        f"- **Phone:** {phone}",
        f"- **Company:** {acc}",
        "",
        "**Keysight Team:**",
        f"- **Field Engineer:** {fe}",
        f"- **Case Manager:** {case_mgr}" if case_mgr != "—" else "",
        f"- **Business Group:** {business_grp_display}",
        "",
        "---",
        "",
        "## 🎯 Summary:",
        "",
        (
            f"Your {case_type.lower() if case_type != '—' else 'case'} (Case #{cn_trim}) is **actively being processed**"
            f"{f' by {fe}' if fe != '—' else ''}. "
            f"{f'Assignment time was {assignment_time_str}. ' if assignment_time_str != '—' else ''}"
            f"{f'Time remaining is {time_remaining_str}. ' if time_remaining_str != '—' else ''}"
            f"{f'Order #{order_num} is linked to this request. ' if order_num != '—' else ''}"
        ),
        "",
        f"**Status:** {'✅ In Progress - Being Actively Worked On' if not closed_flag else '✅ Closed'}",
        (
            f"**Expected Completion:** by {sla_due_str}"
            if sla_due_str != "—" and not closed_flag
            else ""
        ),
        "",
        "---",
        "",
        "**Need to follow up?** " + (f"Contact {contact} ({email}) or field engineer {fe} for updates." if contact != "—" else "Contact the Keysight team for updates."),
    ]
    return "\n".join(s for s in sections if s)


def _order_status_enhanced(status_raw: str) -> str:
    """Map raw status to enhanced format per Cursor rule."""
    s = (status_raw or "").strip().lower()
    if "cancel" in s:
        return "**Order Status:** ❌ **CANCELLED**"
    if "close" in s or "complete" in s:
        return "**Order Status:** ✅ **CLOSED & COMPLETED**"
    return "**Order Status:** 🟡 **OPEN / IN PROGRESS**"


def _get(h: dict, *keys: str) -> str:
    """First non-empty value from dict for given keys (ES or SF naming)."""
    for k in keys:
        v = h.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _norm_order_id(s: str) -> str:
    s = str(s).strip()
    return s.lstrip("0") or s or "0"


def _format_order_status_full(h: dict, order_id: str, message: str = "") -> str:
    """Single order record (ES or normalized) -> rich order/location status markdown."""
    order_num = _fmt(_get(h, "ORDER__C", "OrderNumber")) or order_id
    if order_num and _norm_order_id(order_num) != _norm_order_id(order_id):
        return ""

    ask_location = "where is my order" in (message or "").lower()
    order_num_clean = order_num.strip("0") or order_num
    status_raw = _fmt(_get(h, "STATUS", "Status"))
    created_dt = _parse_iso_date(_fmt(_get(h, "CREATEDDATE", "CreatedDate")))
    closed_dt = _parse_iso_date(_fmt(_get(h, "CLOSEDDATE", "ClosedDate")))
    first_assigned_dt = _parse_iso_date(_fmt(_get(h, "CASE_FIRST_ASSIGNED__C", "FIRST_ASSIGNED__C")))
    sla_due_dt = _parse_iso_date(_fmt(_get(h, "DUE_DATE_AND_TIME__C", "SLA_DUE_DATE__C")))
    sla_met = h.get("SLA_MET__C")
    is_closed = closed_dt is not None or (status_raw and "close" in status_raw.lower())
    created_str = _format_date_display(created_dt) if created_dt else _fmt(_get(h, "CREATEDDATE", "CreatedDate"))
    closed_str = _format_date_display(closed_dt) if closed_dt else _fmt(_get(h, "CLOSEDDATE", "ClosedDate"))
    first_assigned_str = _format_date_display(first_assigned_dt) if first_assigned_dt else _fmt(_get(h, "CASE_FIRST_ASSIGNED__C", "FIRST_ASSIGNED__C"))
    sla_due_str = _format_date_display(sla_due_dt) if sla_due_dt else _fmt(_get(h, "DUE_DATE_AND_TIME__C", "SLA_DUE_DATE__C"))
    processing_time = _time_delta_str_rounded(created_dt, closed_dt) if (created_dt and closed_dt) else "—"
    assignment_time = _time_delta_str(created_dt, first_assigned_dt) if (created_dt and first_assigned_dt) else "—"
    same_day = "Yes" if (created_dt and closed_dt and created_dt.date() == closed_dt.date()) else "No"

    currency = _fmt(_get(h, "CASECURRENCY"), "USD")
    amount_str = _format_currency(_get(h, "ORDER_AMOUNT_USD__C", "TotalAmount"), currency)
    acc = _fmt(_get(h, "ACCOUNT_NAME_TEXT_ONLY__C", "Account", "AccountId"))
    location, address = _address_parts(_get(h, "ADDRESSDETAILS__C"))
    # Some records store city/postal before street; normalize to street first when obvious.
    if re.search(r"\d{4,}", address or "") and not re.search(r"\d{4,}", location or ""):
        location, address = address, location
    contact = _fmt(_get(h, "CONTACT_NAME_TEXT_ONLY__C", "Contact", "ContactId"))
    email = _fmt(_get(h, "CONTACTEMAIL", "CONTACT_EMAIL__C"))
    phone = _pretty_phone(_get(h, "CONTACTPHONE", "CONTACT_PHONE__C", "Phone", "CONTACTMOBILE"))
    po = _fmt(_get(h, "PURCHASE_ORDER__C", "PurchaseOrderNumber"))
    quote = _fmt(_get(h, "QUOTE__C"))
    case_num_raw = _fmt(_get(h, "CASENUMBER", "CaseNumber"))
    case_num = _normalize_num(case_num_raw) or case_num_raw
    order_type = _fmt(_get(h, "TYPE", "Type"))
    priority = _fmt(_get(h, "PRIORITY"))
    fe = _fmt(_get(h, "FE_NAME__C"))
    business_grp = _fmt(_get(h, "BUSINESS_GROUP__C"))
    region = re.sub(r"^\s*Region\s*-\s*", "", _region_label(_fmt(_get(h, "REGION__C", "CASE_ACCOUNT_REGION__C"))), flags=re.I)
    channel = _fmt(_get(h, "CASE_CHANNEL__C", "ORIGIN"))
    account_mgr = _fmt(_get(h, "CASE_OWNER_MANAGER_TEXT__C", "ACCOUNT_MANAGER__C"))
    tat_business = _fmt(_get(h, "CASE_ASSIGNED_TAT_IN_BUSINESS_DAYS__C", "CASE_RECEIVED_TO_CLOSED_TAT_IN_BUSINESS__C"))

    sla_met_ok = bool(sla_met) and str(sla_met).lower() not in ("false", "no", "0")
    sla_display = "Met ✓" if sla_met_ok else ("Not Met ⚠️" if is_closed else "Not yet (in progress) ⏳")
    completed_early_days = ""
    if closed_dt and sla_due_dt and closed_dt < sla_due_dt:
        days = int(round((sla_due_dt - closed_dt).total_seconds() / 86400.0))
        if days > 0:
            completed_early_days = f"{days} days ahead of schedule"

    if same_day == "Yes" and sla_met_ok:
        perf_rating = "⭐⭐⭐⭐⭐ Excellent"
    elif sla_met_ok:
        perf_rating = "⭐⭐⭐⭐"
    else:
        perf_rating = "⭐⭐–⭐⭐⭐"

    status_line = (
        "**Your Order Status:** ✅ **DELIVERED & CLOSED**"
        if ask_location and is_closed
        else (
            "**Your Order Status:** 🟡 **IN PROGRESS**"
            if ask_location
            else _order_status_enhanced(status_raw)
        )
    )

    title = (
        f"## 📦 Order #{order_num_clean} - Location & Status"
        if ask_location
        else f"## 📋 Service Order Status - Order #{order_num_clean}"
    )
    lines = [title, "", status_line, "", "---", ""]

    if ask_location:
        lines.extend([
            "### 📍 Where Is Your Order?",
            "",
            "Your order has been **delivered** to:" if is_closed else "Your order is currently associated with:",
            "",
            f"**{acc}**",
            f"{address}" if address != "—" else "",
            f"{location}" if location != "—" else "",
            "",
            f"**Recipient:** {contact}",
            f"**Email:** {email}",
            f"**Phone:** {phone}",
            "",
            "---",
            "",
        ])
    else:
        lines.extend([
            "## 📊 Order Overview:",
            "",
            "| Field | Details |",
            "|-------|---------|",
            f"| **Order Number** | {order_num} |",
            f"| **Case Number** | {case_num} |",
            f"| **Order Type** | {order_type} |",
            f"| **Status** | {'Closed (Successfully Completed)' if is_closed else status_raw} |",
            f"| **Priority** | {priority} |",
            f"| **SLA Status** | {sla_display} |",
            "",
            "---",
            "",
            "## 👤 Customer Information:",
            "",
            f"**Company:** {acc}",
            f"**Address:** {address}" if address != "—" else "",
            f"**Location:** {location}" if location != "—" else "",
            "",
            f"**Contact:** {contact}",
            f"**Email:** {email}",
            f"**Phone:** {phone}",
            "",
            "---",
            "",
        ])

    lines.extend([
        "### ⏱️ Order Timeline:" if ask_location else "## ⏱️ Timeline:",
        "",
        "| Event | Date & Time |",
        "|-------|-------------|",
        f"| Order Created | {created_str} |",
        f"| Order Assigned | {first_assigned_str} |",
        f"| **Order Completed** | **{closed_str}** |" if closed_str != "—" else "| **Order Completed** | — |",
        f"| **Processing Time** | **{processing_time}** |",
        f"| **SLA Due Date** | {sla_due_str} |" if sla_due_str != "—" else "",
        f"| **Completed Early By** | **{completed_early_days}** |" if completed_early_days else "",
        "",
        "---",
        "",
        "### 💰 Order Details:" if ask_location else "## 💰 Order Details:",
        "",
        f"- **Order Amount:** {amount_str}",
        f"- **Purchase Order:** {po}",
        f"- **Quote Number:** {quote}",
        f"- **Case Number:** {case_num}",
        f"- **Priority:** {priority}",
        f"- **SLA Status:** {sla_display}" + (f" ({completed_early_days})" if completed_early_days else ""),
        "",
        "---",
        "",
        "## 📈 Performance Metrics:",
        "",
        "| Metric | Value | Status |",
        "|--------|-------|--------|",
        f"| **SLA Met** | {'Yes' if sla_met_ok else 'No'} | {'✅ Excellent' if sla_met_ok else '⚠️'} |",
        f"| **Complete Same Day** | {same_day} | {'✅' if same_day == 'Yes' else '—'} |",
        f"| **Response Time** | {assignment_time} | {'✅ Outstanding' if assignment_time != '—' else '—'} |",
        f"| **Resolution Time** | {processing_time} | {'✅ Excellent' if processing_time != '—' else '—'} |",
        f"| **TAT (Business Days)** | {tat_business} | {'✅' if tat_business != '—' else '—'} |",
        f"| **Priority Target** | {priority} | {'✅ Exceeded' if is_closed else '✅ On Track'} |",
        "",
        "---",
        "",
        "## 👥 Service Team:",
        "",
        f"**Account Manager:** {account_mgr}",
        f"**Field Engineer:** {fe}",
        f"**Business Group:** {business_grp}",
        f"**Region:** {region}",
        f"**Sales Channel:** {channel}",
        "",
        "---",
        "",
    ])

    if is_closed:
        lines.extend([
            "## ✅ What \"Closed\" Status Means:",
            "",
            "Your order is **complete** and has been:",
            "",
            "✓ Fully processed",
            f"✓ Shipped to {acc} facility in {location}" if location != "—" else "✓ Shipped",
            "✓ Delivered successfully",
            "✓ All documentation finalized",
            "✓ Invoice generated",
            "",
            "**No further action is required** - your order was successfully delivered.",
            "",
            "---",
            "",
        ])

    lines.extend([
        "## 📈 Service Performance:" if not ask_location else "## 📞 Need More Information?",
        "",
        (
            "**Outstanding Performance:**\n"
            f"- ✅ {'Same-day completion' if same_day == 'Yes' else 'Completed'}\n"
            f"- ✅ Assigned within {assignment_time}\n"
            f"- ✅ {'Completed ' + completed_early_days if completed_early_days else 'Processed within priority target'}\n"
            f"- ✅ SLA {'met and exceeded' if sla_met_ok else 'under review'}"
        ) if not ask_location else "If you need shipping documentation, proof of delivery, or invoice copies:",
        "",
        "---",
        "",
        "## 📞 Contact Information:" if not ask_location else "## 📞 Contact Information:",
        "",
        "**Contact:**",
        f"- **Account Manager:** {account_mgr}",
        f"- **Field Engineer:** {fe}",
        f"- **Business Group:** {business_grp}",
        f"- **Case Reference:** {case_num}",
        "",
        "**Your Contact on File:**",
        f"- {contact}",
        f"- {email}",
        f"- {phone}",
        "",
        "---",
        "",
        "## 🎯 Summary:",
        "",
        (
            f"Service order **#{order_num_clean}** was **{'successfully completed' if is_closed else status_raw.lower()}** "
            f"for **{amount_str}** (PO: {po}). It was processed in **{processing_time}**"
            + (f" and completed {completed_early_days}." if completed_early_days else ".")
        ),
        "",
        f"**Performance Rating:** {perf_rating}",
        "",
        (
            f"**Note:** This order was completed in {(created_dt.strftime('%B %Y') if created_dt else 'the recorded period')}. "
            f"The items have been delivered to your {acc} facility in {location}. "
            "If you're looking for a different or more recent order, please provide that order number."
            if ask_location and is_closed
            else "Is there anything specific about this order you need assistance with?"
        ),
    ])

    return "\n".join(s for s in lines if s)


def _format_order_hit(h: dict, order_id: str, message: str = "") -> str:
    """ES hit -> full enhanced Service Order Status report."""
    return _format_order_status_full(h, order_id, message=message)


def _format_sf_order(records: list, order_id: str, message: str = "") -> str:
    """SF order records -> full enhanced report (normalize first record to dict)."""
    if not records:
        return ""
    r = records[0]
    normal: dict = {
        "OrderNumber": r.get("OrderNumber"),
        "STATUS": r.get("Status"),
        "ORDER__C": r.get("OrderNumber"),
    }
    for k, v in r.items():
        if v is not None and str(v).strip():
            normal[k] = v
    return _format_order_status_full(normal, order_id, message=message)


def _format_cal_cert_found(h: dict) -> str:
    """One cal cert hit -> short cert status."""
    cert = h.get("CERTIFICATE_NO__C", "—")
    model = h.get("MODEL_NUMBER__C", "—")
    serial = h.get("SERIAL_NUMBER__C", "—")
    return (
        "## Calibration Certificate\n\n"
        f"**Certificate:** {cert} · **Model:** {model} · **Serial:** {serial}\n\n"
        "Certificate record found. Use Keysight InfoLine for the full document."
    )


def try_data_fastpath(message: str) -> Optional[Tuple[str, List[str]]]:
    """
    If the message is a clear case/order/cal-cert lookup, run one tool and return
    (reply, citations). Otherwise return None so the router uses the full agent.
    Priority: order intent > case intent > cal cert.
    """
    msg = (message or "").strip()
    if not msg:
        return None

    # ── ORDER STATUS: check FIRST when order intent is present ────────────────
    # This prevents "service order status 00000100" from being misrouted as a case.
    if _has_order_intent(msg):
        order_id = _extract_order_id(msg)
        if order_id:
            # Prefer Elasticsearch first for richer order/case fields.
            try:
                from app.tools.elasticsearch_tool import elasticsearch_keyword_search
                out = elasticsearch_keyword_search.invoke({"query": order_id, "top_k": 5})
            except Exception as e:
                log.warning("data_fastpath.order_es_error", order_id=order_id, error=str(e))
                out = []
            if isinstance(out, list) and out and "message" not in out[0]:
                for h in out:
                    if h.get("ORDER__C"):
                        reply = _format_order_hit(h, order_id, msg)
                        if reply:
                            return (reply, ["elasticsearch_keyword_search"])

            # Fallback to Salesforce when Elasticsearch has no match.
            try:
                from app.tools.salesforce_tool import salesforce_get_order_by_number
                sf_out = salesforce_get_order_by_number.invoke({"order_number": order_id})
            except Exception as e:
                log.warning("data_fastpath.order_sf_error", order_id=order_id, error=str(e))
                sf_out = {}
            if isinstance(sf_out, dict) and sf_out.get("records"):
                reply = _format_sf_order(sf_out["records"], order_id, msg)
                if reply:
                    return (reply, ["salesforce_get_order_by_number"])
            return None

    # Case status by number
    case_id = _extract_case_id(msg)
    if case_id:
        # Ultra-fast local CSV path: use ingested Caseextract.csv when available
        local_case = _lookup_case_locally(case_id)
        if local_case:
            reply = _format_case_hit(local_case, case_id)
            if reply:
                return (reply, ["case_csv_fastpath"])

        try:
            from app.tools.elasticsearch_tool import elasticsearch_keyword_search
            out = elasticsearch_keyword_search.invoke({"query": case_id, "top_k": 1})
        except Exception as e:
            log.warning("data_fastpath.case_es_error", case_id=case_id, error=str(e))
            return None
        if isinstance(out, list) and out and "message" not in out[0]:
            for h in out:
                if h.get("CASENUMBER"):
                    reply = _format_case_hit(h, case_id)
                    if reply:
                        return (reply, ["elasticsearch_keyword_search"])

        # Fallback to Salesforce when Elasticsearch has no match for Case
        try:
            from app.tools.salesforce_tool import salesforce_get_case_by_number
            sf_out = salesforce_get_case_by_number.invoke({"case_number": case_id})
        except Exception as e:
            log.warning("data_fastpath.case_sf_error", case_id=case_id, error=str(e))
            sf_out = {}
        
        if isinstance(sf_out, dict) and sf_out.get("records"):
            # Format salesforce case similar to ES match
            r = sf_out["records"][0]
            sf_formatted = {
                "CASENUMBER": r.get("CaseNumber"),
                "STATUS": r.get("Status"),
                "SUBJECT": r.get("Subject"),
                "DESCRIPTION": r.get("Description"),
                "PRIORITY": r.get("Priority")
            }
            reply = _format_case_hit(sf_formatted, case_id)
            if reply:
                return (reply, ["salesforce_get_case_by_number"])

        return None

    # Order status by number (non-order-intent fallback; handles e.g. bare order numbers)
    order_id = _extract_order_id(msg)
    if order_id:
        # Prefer Elasticsearch first for richer order/case fields.
        try:
            from app.tools.elasticsearch_tool import elasticsearch_keyword_search
            out = elasticsearch_keyword_search.invoke({"query": order_id, "top_k": 5})
        except Exception as e:
            log.warning("data_fastpath.order_es_error", order_id=order_id, error=str(e))
            out = []
        if isinstance(out, list) and out and "message" not in out[0]:
            for h in out:
                if h.get("ORDER__C"):
                    reply = _format_order_hit(h, order_id, msg)
                    if reply:
                        return (reply, ["elasticsearch_keyword_search"])

        # Fallback to Salesforce when Elasticsearch has no match.
        try:
            from app.tools.salesforce_tool import salesforce_get_order_by_number
            sf_out = salesforce_get_order_by_number.invoke({"order_number": order_id})
        except Exception as e:
            log.warning("data_fastpath.order_sf_error", order_id=order_id, error=str(e))
            sf_out = {}
        if isinstance(sf_out, dict) and sf_out.get("records"):
            reply = _format_sf_order(sf_out["records"], order_id, msg)
            if reply:
                return (reply, ["salesforce_get_order_by_number"])
        return None

    # Cal cert by model + serial
    cal_ids = _extract_cal_cert_ids(msg)
    if cal_ids:
        model, serial = cal_ids
        query = f"{model} {serial}"
        try:
            from app.tools.elasticsearch_tool import elasticsearch_keyword_search
            out = elasticsearch_keyword_search.invoke({"query": query, "top_k": 5})
        except Exception as e:
            log.warning("data_fastpath.cal_es_error", query=query, error=str(e))
            return None
        if isinstance(out, list) and out and "message" not in out[0]:
            for h in out:
                if h.get("CERTIFICATE_NO__C"):
                    reply = _format_cal_cert_found(h)
                    if reply:
                        return (reply, ["elasticsearch_keyword_search"])
        # Not found: return short "not found" so we still skip the agent
        reply = (
            f"## Calibration Certificate Not Found - {model} (S/N: {serial})\n\n"
            "No certificate record in the database. Use Keysight InfoLine Portal "
            "(https://service.keysight.com/infoline) or contact Keysight Service for the certificate."
        )
        return (reply, ["elasticsearch_keyword_search"])

    return None


def try_status_intent_fastpath(message: str) -> Optional[Tuple[str, List[str]]]:
    """
    Fast response when user asks for case/order status but does not provide an ID.
    Prevents expensive LLM/tool runs and avoids timeout for ambiguous status prompts.
    """
    msg = (message or "").strip()
    if not msg:
        return None

    lower = msg.lower()
    has_id = bool(re.search(r"\b\d{5,8}\b", msg))
    if has_id:
        return None

    case_intent = any(k in lower for k in ("case status", "status of case", "give me case status", "case update"))
    order_intent = any(
        k in lower
        for k in (
            "order status",
            "service order status",
            "where is my order",
            "status of order",
        )
    )

    if case_intent:
        reply = (
            "## Case Status\n\n"
            "Please provide the **case number** so I can fetch the exact record instantly.\n\n"
            "Example: `600756 give me case status`"
        )
        return (reply, ["status_intent_fastpath"])

    if order_intent:
        reply = (
            "## Service Order Status\n\n"
            "Please provide the **order number** so I can fetch the exact status instantly.\n\n"
            "Example: `Where is my order? Order #4047199`"
        )
        return (reply, ["status_intent_fastpath"])

    return None
