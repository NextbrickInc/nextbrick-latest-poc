# backend/app/tools/salesforce_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Salesforce LangChain tools — OAuth2 client_credentials + REST API.
#
# Configure in .env:
#   SF_TOKEN_URL      = https://your-instance.my.salesforce.com/services/oauth2/token
#   SF_CLIENT_ID      = your_connected_app_client_id
#   SF_CLIENT_SECRET  = your_connected_app_client_secret
#   SF_API_BASE_URL   = https://your-instance.my.salesforce.com/services/data/v60.0
#
# Tools: get_all_orders, get_order, get_case, create_case, query (SOQL).
# Agent prompt is built from tool descriptions in agent_service — no hardcoded keywords.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import structlog
import time
from typing import Any, Optional

import httpx
from langchain_core.tools import tool

from app.config import settings

log = structlog.get_logger(__name__)

# In-memory token cache (token_string, expires_at_ts)
_token_cache: tuple[str, float] = ("", 0)
TOKEN_BUFFER_SECONDS = 60
# Last token error message (for tool responses when token fails)
_last_token_error: Optional[str] = None


def _get_bearer_token() -> Optional[str]:
    """Obtain Bearer token via OAuth2 (client_credentials, then password fallback). Cached until near expiry."""
    global _token_cache, _last_token_error
    now = time.time()
    if _token_cache[0] and _token_cache[1] > now + TOKEN_BUFFER_SECONDS:
        return _token_cache[0]

    token_url = getattr(settings, "sf_token_url", None)
    client_id = getattr(settings, "sf_client_id", None)
    client_secret = getattr(settings, "sf_client_secret", None)
    if not token_url or not client_id or not client_secret:
        _last_token_error = "Missing config: set SF_TOKEN_URL, SF_CLIENT_ID, and SF_CLIENT_SECRET in .env"
        log.warning("salesforce.token_missing_config")
        return None

    # 1) Try client_credentials (requires "Enable Client Credentials Flow" in Connected App)
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.status_code == 200:
                data = r.json()
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 7200)
                if access_token:
                    _token_cache = (access_token, now + expires_in)
                    _last_token_error = None
                    return access_token
            # Capture Salesforce error for diagnostics
            try:
                err_body = r.json()
                err_msg = err_body.get("error_description") or err_body.get("error") or r.text
            except Exception:
                err_msg = r.text or f"HTTP {r.status_code}"
            _last_token_error = f"Client credentials failed ({r.status_code}): {err_msg}"
            log.error("salesforce.token_error", status=r.status_code, detail=err_msg)
    except Exception as e:
        _last_token_error = f"Token request error: {e!s}"
        log.error("salesforce.token_error", error=str(e))

    # 2) Fallback: username-password flow (no Connected App client-credentials needed)
    username = getattr(settings, "sf_username", None)
    password = getattr(settings, "sf_password", None)
    security_token = getattr(settings, "sf_security_token", None) or ""
    if username and password:
        try:
            with httpx.Client(timeout=30.0) as client:
                pwd = f"{password}{security_token}".strip()
                r = client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "username": username,
                        "password": pwd,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if r.status_code == 200:
                    data = r.json()
                    access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 7200)
                    if access_token:
                        _token_cache = (access_token, now + expires_in)
                        _last_token_error = None
                        return access_token
                try:
                    err_body = r.json()
                    err_msg = err_body.get("error_description") or err_body.get("error") or r.text
                except Exception:
                    err_msg = r.text or f"HTTP {r.status_code}"
                _last_token_error = f"Password flow failed ({r.status_code}): {err_msg}"
                log.error("salesforce.token_password_error", status=r.status_code, detail=err_msg)
        except Exception as e:
            _last_token_error = f"Password token error: {e!s}"
            log.error("salesforce.token_error", error=str(e))

    if not _last_token_error:
        _last_token_error = "Token request failed (no token returned)."
    return None


def _get_salesforce_error_message() -> str:
    """Return the last token/config error for inclusion in tool responses."""
    if _last_token_error:
        return _last_token_error
    base = getattr(settings, "sf_api_base_url", None)
    if not base:
        return "Missing config: set SF_API_BASE_URL in .env"
    return "Salesforce not configured or token failed."


def _soql_escape(value: str) -> str:
    """Escape single quotes for SOQL string literals (double the quote)."""
    return (value or "").replace("'", "''")


def _sf_request(method: str, path: str, params: Optional[dict] = None, json: Optional[dict] = None) -> Any:
    """Call Salesforce REST API with Bearer token. path is relative to SF_API_BASE_URL."""
    global _last_token_error
    base = getattr(settings, "sf_api_base_url", None)
    if not base:
        _last_token_error = "Missing config: set SF_API_BASE_URL in .env"
        log.warning("salesforce.api_base_missing")
        return None
    token = _get_bearer_token()
    if not token:
        return None
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.request(
                method,
                url,
                params=params,
                json=json,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            r.raise_for_status()
            if r.content:
                return r.json()
            return {}
    except Exception as e:
        log.error("salesforce.request_error", method=method, path=path, error=str(e))
        return None


# ── Tool 1: Get all orders (with order items) ──────────────────────────────────

@tool
def salesforce_get_all_orders() -> dict:
    """
    Get all Orders from Salesforce with their line items (OrderItems).
    Returns Id, OrderNumber, Status, and for each order the related order items (id, UnitPrice, Quantity).
    ALWAYS use this when the user asks to list orders, get all orders, show orders, or see the order list. Do not respond without calling this tool first.
    """
    log.info("salesforce.get_all_orders")
    soql = "SELECT Id, OrderNumber, Status, (SELECT Id, UnitPrice, Quantity FROM OrderItems) FROM Order"
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message(), "records": []}
    records = result.get("records", [])
    log.info("salesforce.get_all_orders.done", total=len(records))
    return {"totalSize": result.get("totalSize", 0), "records": records}


# ── Tool 2: Get order by Order Number ─────────────────────────────────────────

@tool
def salesforce_get_order_by_number(order_number: str) -> dict:
    """
    Get the details of a specific order by its Order Number (e.g. 00000100).
    Returns Id, OrderNumber, Status, and line items (OrderItems: id, UnitPrice, Quantity).
    Use when the user asks for a specific order by order number.
    """
    log.info("salesforce.get_order_by_number", order_number=order_number)
    safe = _soql_escape(order_number.strip())
    soql = (
        "SELECT Id, OrderNumber, Status, (SELECT Id, UnitPrice, Quantity FROM OrderItems) FROM Order "
        f"WHERE OrderNumber = '{safe}'"
    )
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message()}
    records = result.get("records", [])
    if not records:
        return {"error": f"No order found for OrderNumber: {order_number}", "records": []}
    return {"records": records, "totalSize": len(records)}


# ── Tool 2b: Get single order by Id (legacy) ───────────────────────────────────

@tool
def salesforce_get_order(order_id: str) -> dict:
    """
    Retrieve one Salesforce Order by its Id (18-character Salesforce Id).
    Returns order status, line items (OrderItems), and details.
    Use when the user provides an Order Id (e.g. 801fj00000jyqgEAAQ).
    """
    log.info("salesforce.get_order", order_id=order_id)
    soql = (
        "SELECT Id, OrderNumber, Status, (SELECT Id, UnitPrice, Quantity FROM OrderItems) FROM Order "
        f"WHERE Id = '{_soql_escape(order_id)}'"
    )
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message()}
    records = result.get("records", [])
    if not records:
        return {"error": f"No order found for Id: {order_id}", "records": []}
    return {"records": records, "totalSize": len(records)}


# ── Tool 3: Get product price by product name ──────────────────────────────────

@tool
def salesforce_get_product_price(product_name: str) -> dict:
    """
    Get the standard price for a specific product by name (e.g. DSOX1202A).
    Returns PricebookEntry id, UnitPrice, and Pricebook2 name.
    Use when the user asks for the price of a product, e.g. "What is the price of DSOX1202A?" or "Get the price for product X."
    """
    log.info("salesforce.get_product_price", product_name=product_name)
    safe = _soql_escape(product_name.strip())
    soql = (
        "SELECT Id, UnitPrice, Pricebook2.Name FROM PricebookEntry "
        f"WHERE Product2.Name = '{safe}' AND UseStandardPrice = true"
    )
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message(), "records": []}
    records = result.get("records", [])
    return {"totalSize": result.get("totalSize", 0), "records": records}


# ── Tool 4: Get cases by account name ───────────────────────────────────────────

@tool
def salesforce_get_cases_by_account(account_name: str) -> dict:
    """
    Get case details (id, case number) for cases belonging to an account by the account name.
    User passes the account name (e.g. "Test Account"). Use when the user asks for cases by account name.
    """
    log.info("salesforce.get_cases_by_account", account_name=account_name)
    safe = _soql_escape(account_name.strip())
    soql = f"SELECT Id, CaseNumber FROM Case WHERE Account.Name = '{safe}'"
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message(), "records": []}
    records = result.get("records", [])
    return {"totalSize": result.get("totalSize", 0), "records": records}


# ── Get case by Id ─────────────────────────────────────────────────────────────

@tool
def salesforce_get_case(case_id: str) -> dict:
    """
    Retrieve a Salesforce Support Case by its Case Id.
    Returns status, subject, description, priority, owner.
    Use when the user asks about a specific case or ticket by ID.
    """
    log.info("salesforce.get_case", case_id=case_id)
    path = f"sobjects/Case/{case_id}"
    result = _sf_request("GET", path)
    if result is None:
        return {"error": _get_salesforce_error_message()}
    return result


# ── Tool 5b: Get case by CaseNumber ──────────────────────────────────────────

@tool
def salesforce_get_case_by_number(case_number: str) -> dict:
    """
    Get the details of a specific case by its CaseNumber (e.g. 00001027 or 600756).
    Returns CaseNumber, Status, Subject, Priority, and Description.
    ALWAYS use this when the user asks for a specific case status by its case number.
    """
    log.info("salesforce.get_case_by_number", case_number=case_number)
    num = case_number.strip()
    safe = _soql_escape(num)
    padded = _soql_escape(num.zfill(8))
    
    soql = (
        "SELECT Id, CaseNumber, Status, Subject, Priority, Description FROM Case "
        f"WHERE CaseNumber = '{safe}' OR CaseNumber = '{padded}'"
    )
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message()}
    
    records = result.get("records", [])
    if not records:
        return {"error": f"No case found for CaseNumber: {case_number}", "records": []}
    return {"records": records, "totalSize": len(records)}


# ── Tool 6: Create case (subject + description; rest default) ──────────────────

# Default AccountId for new cases (configurable via settings if needed)
_DEFAULT_CASE_ACCOUNT_ID = "001fj00000jzVxrAAE"


@tool
def salesforce_create_case(subject: str, description: str, priority: str = "Medium") -> dict:
    """
    Create a new Salesforce Support Case. Requires subject and description from the user.
    If subject or description is missing, do not call this tool — ask the user to provide both, then create the case once they reply.
    Status, Origin, and AccountId use defaults. Priority: Low, Medium, High, or Critical.
    """
    subject = (subject or "").strip()
    description = (description or "").strip()
    missing = []
    if not subject:
        missing.append("subject")
    if not description:
        missing.append("description")
    if missing:
        return {
            "error": "missing_required",
            "message": "Please provide both a subject and a description to create the case. Reply with the subject and description, then I will create the case.",
            "missing": missing,
            "success": False,
        }
    log.info("salesforce.create_case", subject=subject, priority=priority)
    account_id = getattr(settings, "sf_default_case_account_id", None) or _DEFAULT_CASE_ACCOUNT_ID
    body = {
        "Subject": subject,
        "Status": "New",
        "Priority": priority,
        "Origin": "Web",
        "Description": description,
        "AccountId": account_id,
    }
    result = _sf_request("POST", "sobjects/Case", json=body)
    if result is None:
        return {"error": _get_salesforce_error_message(), "id": None, "success": False}
    new_id = result.get("id")
    return {"id": new_id, "success": True, "subject": subject}


# ── Generic SOQL query ────────────────────────────────────────────────────────

@tool
def salesforce_query(soql: str) -> dict:
    """
    Run a SOQL query against Salesforce (e.g. SELECT Id, Name FROM Account LIMIT 10).
    Use for custom queries when other tools do not fit: list accounts, contacts, or other objects.
    """
    log.info("salesforce.query", soql_preview=soql[:80])
    result = _sf_request("GET", "query", params={"q": soql})
    if result is None:
        return {"error": _get_salesforce_error_message(), "records": []}
    return {"totalSize": result.get("totalSize", 0), "records": result.get("records", [])}
