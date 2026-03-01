# backend/app/tools/salesforce_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Salesforce LangChain tools.
#
# CURRENT STATE: Stub / mock implementation that returns realistic demo data.
# HOW TO ADD REAL INTEGRATION:
#   1. pip install simple-salesforce
#   2. Set SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, SF_DOMAIN in .env
#   3. Replace the body of each function below with real Salesforce API calls.
#   4. The @tool decorator and function signature MUST stay the same — the
#      agent service will pick up the change automatically.
#
# Example real implementation snippet:
#   from simple_salesforce import Salesforce
#   from app.config import settings
#   def _get_sf_client():
#       return Salesforce(
#           username=settings.sf_username,
#           password=settings.sf_password,
#           security_token=settings.sf_security_token,
#           domain=settings.sf_domain,
#       )
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import structlog
from langchain_core.tools import tool

log = structlog.get_logger(__name__)


@tool
def salesforce_get_case(case_id: str) -> dict:
    """
    Retrieve the details of a Salesforce Support Case by its Case ID.
    Returns status, subject, description, priority, and owner information.
    Use this when the user asks about a specific case or ticket.
    """
    log.info("salesforce.get_case", case_id=case_id)

    # ── STUB: Replace with real Salesforce API call ───────────────────────────
    # sf = _get_sf_client()
    # result = sf.Case.get(case_id)
    # return dict(result)
    return {
        "id": case_id,
        "subject": f"[Mock] Issue with product — Case {case_id}",
        "status": "In Progress",
        "priority": "High",
        "description": "Customer reported intermittent connectivity issues.",
        "owner": "Support Team EMEA",
        "created_date": "2026-02-28T09:00:00Z",
        "last_modified": "2026-03-01T08:45:00Z",
        "_source": "salesforce_mock",
    }


@tool
def salesforce_create_case(subject: str, description: str, priority: str = "Medium") -> dict:
    """
    Create a new Salesforce Support Case.
    Use this when the user wants to open a new case, ticket, or support request.
    Priority must be one of: Low, Medium, High, Critical.
    Returns the newly created Case ID and a confirmation.
    """
    log.info("salesforce.create_case", subject=subject, priority=priority)

    # ── STUB: Replace with real Salesforce API call ───────────────────────────
    # sf = _get_sf_client()
    # result = sf.Case.create({
    #     "Subject": subject,
    #     "Description": description,
    #     "Priority": priority,
    # })
    # return {"id": result["id"], "status": "Created"}
    mock_id = f"CASE-{abs(hash(subject)) % 900000 + 100000}"
    return {
        "id": mock_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "New",
        "created": True,
        "_source": "salesforce_mock",
    }


@tool
def salesforce_get_order(order_id: str) -> dict:
    """
    Retrieve the status and details of a Salesforce Order by its Order ID.
    Returns order status, line items, shipping address, and expected delivery date.
    Use this when the user asks about an order, shipment, or delivery.
    """
    log.info("salesforce.get_order", order_id=order_id)

    # ── STUB: Replace with real Salesforce API call ───────────────────────────
    # sf = _get_sf_client()
    # result = sf.Order.get(order_id)
    # return dict(result)
    return {
        "id": order_id,
        "status": "Shipped",
        "account": "Nextbrick GmbH",
        "total_amount": 4850.00,
        "currency": "EUR",
        "line_items": [
            {"product": "Industrial IoT Sensor v3", "qty": 10, "unit_price": 485.00}
        ],
        "shipping_address": "Industriestraße 12, 80339 München, Germany",
        "expected_delivery": "2026-03-05",
        "tracking_number": "DHL-DE-78234590",
        "_source": "salesforce_mock",
    }
