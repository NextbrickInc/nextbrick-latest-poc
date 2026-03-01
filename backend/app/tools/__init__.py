# backend/app/tools/__init__.py
# ─────────────────────────────────────────────────────────────────────────────
# Aggregates every LangChain @tool into a single ALL_TOOLS list that the
# agent service binds to the ReAct agent.
# ─────────────────────────────────────────────────────────────────────────────
from app.tools.salesforce_tool import (
    salesforce_get_case,
    salesforce_create_case,
    salesforce_get_order,
)
from app.tools.confluence_tool import (
    confluence_search,
    confluence_get_page,
)
from app.tools.elasticsearch_tool import (
    elasticsearch_semantic_search,
    elasticsearch_ingest_document,
)

ALL_TOOLS = [
    # Salesforce
    salesforce_get_case,
    salesforce_create_case,
    salesforce_get_order,
    # Confluence
    confluence_search,
    confluence_get_page,
    # Elasticsearch / Vector Search
    elasticsearch_semantic_search,
    elasticsearch_ingest_document,
]

__all__ = ["ALL_TOOLS"]
