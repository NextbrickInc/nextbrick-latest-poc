# backend/app/tools/confluence_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Confluence LangChain tools.
#
# CURRENT STATE: Stub / mock implementation returning realistic demo KB pages.
# HOW TO ADD REAL INTEGRATION:
#   1. pip install atlassian-python-api
#   2. Set CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN,
#      CONFLUENCE_SPACE_KEY in .env
#   3. Replace the body of each function below with real Confluence API calls.
#
# Example real implementation snippet:
#   from atlassian import Confluence
#   from app.config import settings
#   def _get_confluence_client():
#       return Confluence(
#           url=settings.confluence_url,
#           username=settings.confluence_username,
#           password=settings.confluence_api_token,
#           cloud=True,
#       )
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import structlog
from langchain_core.tools import tool

log = structlog.get_logger(__name__)

# ── Mock knowledge base ───────────────────────────────────────────────────────
_MOCK_PAGES = [
    {
        "id": "101",
        "title": "IoT Sensor Installation Guide",
        "space": "PRODUCTS",
        "excerpt": "Step-by-step guide for installing and configuring IoT sensors in industrial environments. Covers mounting, wiring, firmware update, and first-boot calibration.",
        "url": "https://confluence.nextbrick.com/display/PRODUCTS/iot-sensor-installation",
        "last_modified": "2026-02-15",
    },
    {
        "id": "102",
        "title": "Customer Onboarding Checklist",
        "space": "CS",
        "excerpt": "Standard onboarding process for new enterprise customers: account setup, license activation, training schedule, and go-live sign-off criteria.",
        "url": "https://confluence.nextbrick.com/display/CS/customer-onboarding",
        "last_modified": "2026-01-20",
    },
    {
        "id": "103",
        "title": "Calibration Certificate Process",
        "space": "QUALITY",
        "excerpt": "How to request, track, and download calibration certificates for Nextbrick instruments. Covers portal login, asset lookup, and certificate PDF download.",
        "url": "https://confluence.nextbrick.com/display/QUALITY/calibration-cert",
        "last_modified": "2026-02-01",
    },
    {
        "id": "104",
        "title": "Escalation Matrix — Tier 2 Support",
        "space": "SUPPORT",
        "excerpt": "Defines when and how to escalate support cases to Tier 2 engineering. Includes SLA thresholds, contact list, and Jira escalation template.",
        "url": "https://confluence.nextbrick.com/display/SUPPORT/escalation-matrix",
        "last_modified": "2026-02-20",
    },
    {
        "id": "105",
        "title": "Pricing & Discount Policy FY2026",
        "space": "SALES",
        "excerpt": "Approved discount tiers, regional pricing adjustments, and CPQ configuration rules for FY2026. Requires Sales VP approval for discounts above 25%.",
        "url": "https://confluence.nextbrick.com/display/SALES/pricing-policy-fy2026",
        "last_modified": "2026-01-05",
    },
]


@tool
def confluence_search(query: str) -> list:
    """
    Search the Confluence knowledge base for articles and documentation matching a query.
    Returns a ranked list of pages with title, excerpt, space, and URL.
    Use this when the user asks about internal processes, guides, policies, or how-to docs.
    """
    log.info("confluence.search", query=query)

    # ── STUB: Replace with real Confluence CQL search ─────────────────────────
    # cf = _get_confluence_client()
    # results = cf.cql(
    #     f'type=page AND space="{settings.confluence_space_key}" AND text~"{query}"',
    #     limit=5
    # )
    # return [{"id": p["id"], "title": p["title"], "url": p["_links"]["webui"]} ...]

    q = query.lower()
    matched = [
        p for p in _MOCK_PAGES
        if any(word in p["title"].lower() or word in p["excerpt"].lower()
               for word in q.split())
    ]
    return matched[:3] if matched else _MOCK_PAGES[:2]


@tool
def confluence_get_page(page_id: str) -> dict:
    """
    Retrieve the full content of a specific Confluence page by its page ID.
    Use this after confluence_search to get the detailed body of a page.
    Returns title, space, full body content, and URL.
    """
    log.info("confluence.get_page", page_id=page_id)

    # ── STUB: Replace with real Confluence page fetch ─────────────────────────
    # cf = _get_confluence_client()
    # page = cf.get_page_by_id(page_id, expand="body.storage")
    # return {"id": page["id"], "title": page["title"], "content": page["body"]["storage"]["value"]}

    page = next((p for p in _MOCK_PAGES if p["id"] == page_id), None)
    if not page:
        return {"error": f"Page {page_id} not found", "_source": "confluence_mock"}
    return {**page, "content": f"[Full content of '{page['title']}' — replace with real Confluence API call]", "_source": "confluence_mock"}
