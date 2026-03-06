# backend/app/tools/__init__.py
# Aggregates all LangChain tools for the ReAct agent.
from app.tools.salesforce_tool import (
    salesforce_get_all_orders,
    salesforce_get_order,
    salesforce_get_order_by_number,
    salesforce_get_product_price,
    salesforce_get_cases_by_account,
    salesforce_get_case,
    salesforce_get_case_by_number,
    salesforce_create_case,
    salesforce_query,
)
from app.tools.confluence_tool import (
    confluence_search,
    confluence_get_page,
)
from app.tools.elasticsearch_tool import (
    elasticsearch_keyword_search,
    elasticsearch_semantic_search,
    elasticsearch_ingest_document,
    elasticsearch_websearch,
)
from app.tools.elasticsearch_ollama_tool import (
    elasticsearch_ollama_semantic_search,
    elasticsearch_ollama_ingest_document,
)

ALL_TOOLS = [
    # Salesforce (OAuth2)
    salesforce_get_all_orders,
    salesforce_get_order,
    salesforce_get_order_by_number,
    salesforce_get_product_price,
    salesforce_get_cases_by_account,
    salesforce_get_case,
    salesforce_get_case_by_number,
    salesforce_create_case,
    salesforce_query,
    # Confluence
    confluence_search,
    confluence_get_page,
    elasticsearch_keyword_search,
    elasticsearch_websearch,
    # Elasticsearch — BGE-M3 semantic search (HuggingFace)
    elasticsearch_semantic_search,
    elasticsearch_ingest_document,
    # Elasticsearch — Ollama bge-m3:latest, index next_elastic_test3 (docs)
    elasticsearch_ollama_semantic_search,
    elasticsearch_ollama_ingest_document,
]

__all__ = ["ALL_TOOLS"]
