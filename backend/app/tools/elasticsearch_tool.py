# backend/app/tools/elasticsearch_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Fixed: queries next_elastic_test1 (real case/order/product data) using
# both keyword search and semantic search via BGE-M3 embeddings.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import re
import structlog
from typing import Optional
from langchain_core.tools import tool

log = structlog.get_logger(__name__)

_embeddings = None
_vector_store = None


def _get_embeddings():
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    from app.config import settings
    model_name = getattr(settings, "embedding_model", "BAAI/bge-m3")
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        log.info("bge_m3.embedder_ready", model=model_name)
    except Exception as e:
        log.error("bge_m3.embedder_failed", error=str(e))
        _embeddings = None
    return _embeddings


def _get_es_client():
    from app.config import settings
    from elasticsearch import Elasticsearch
    kwargs = {"hosts": [settings.es_host]}
    if settings.es_username and settings.es_password:
        kwargs["basic_auth"] = (settings.es_username, settings.es_password)
    return Elasticsearch(**kwargs)


def _get_vector_store():
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    from app.config import settings
    embeddings = _get_embeddings()
    if embeddings is None:
        return None
    try:
        from langchain_elasticsearch import ElasticsearchStore
        es_client = _get_es_client()
        _vector_store = ElasticsearchStore(
            client=es_client,
            index_name=settings.es_vector_index,
            embedding=embeddings,
        )
        log.info("elasticsearch_tool.vector_store_ready", index=settings.es_vector_index)
    except Exception as e:
        log.error("elasticsearch_tool.vector_store_failed", error=str(e))
        _vector_store = None
    return _vector_store


def _extract_id_tokens(query: str) -> list[str]:
    """Extract probable ID tokens (orders, cases, serials, certs) from free text."""
    if not query:
        return []
    tokens = re.findall(r"[A-Za-z0-9\\-]+", query)
    ids: list[str] = []
    for t in tokens:
        if re.fullmatch(r"\\d{5,}", t):  # pure numbers like 600756, 4047199, 300655472
            ids.append(t)
        elif any(ch.isdigit() for ch in t) and len(t) >= 5:
            ids.append(t)
    return ids


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def elasticsearch_keyword_search(query: str, top_k: int = 5) -> list:
    """
    Search real Keysight case, order, asset, and product data using an ID-aware strategy.

    - For queries containing order/case/serial/certificate numbers (e.g. "600756 give me case status"),
      first extract ID tokens and run exact term queries on ORDER__C, CASENUMBER,
      SERIAL_NUMBER__C, and CERTIFICATE_NO__C in the `next_elastic_test1` index.
    - If no exact ID match is found, fall back to a broader multi_match keyword search
      across key fields (ORDER__C, CASENUMBER, SERIAL_NUMBER__C, MODEL_NUMBER__C, etc.).
    Returns one dict per Elasticsearch document with the most relevant fields populated.
    """
    log.info("elasticsearch.keyword_search", query=query)
    try:
        from app.config import settings
        es = _get_es_client()

        # Use the main data index
        data_index = getattr(settings, "es_data_index", "next_elastic_test1")

        # ── Step 1: Try exact ID-based lookup ─────────────────────────────────
        id_tokens = _extract_id_tokens(query)
        hits = []
        if id_tokens:
            should_terms = []
            for token in id_tokens:
                # For numeric IDs, also search zero-padded variants (e.g. case 600756 → CASENUMBER 00600756)
                variants = {token}
                if token.isdigit():
                    try:
                        n = int(token)
                        # Common lengths: 6-digit case → 8-digit stored; keep raw and zero-padded to 8
                        variants.add(str(n).zfill(8))
                        # Also 7-digit just in case
                        variants.add(str(n).zfill(7))
                    except ValueError:
                        pass
                for v in variants:
                    should_terms.extend(
                        [
                            {"term": {"ORDER__C": v}},
                            {"term": {"CASENUMBER": v}},
                            {"term": {"SERIAL_NUMBER__C": v}},
                            {"term": {"CERTIFICATE_NO__C": v}},
                        ]
                    )
            id_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": should_terms,
                        "minimum_should_match": 1,
                    }
                },
            }
            res_id = es.search(index=data_index, body=id_body)
            hits = res_id["hits"]["hits"]

        # ── Step 2: Fallback to broader keyword search ────────────────────────
        if not hits:
            body = {
                "size": top_k,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "ORDER__C^5",
                            "CASENUMBER^5",
                            "SERIAL_NUMBER__C^5",
                            "CERTIFICATE_NO__C^5",
                            "MODEL_NUMBER__C^4",
                            "TITLE^3",
                            "PRODUCT_TITLE^3",
                            "SUBJECT^3",
                            "ACCOUNT_NAME_TEXT_ONLY__C^2",
                            "DESCRIPTION",
                            "CASE_RESOLUTION__C",
                            "STATUS",
                            "TYPE",
                        ],
                        "type": "best_fields",
                    }
                },
            }

            res_kw = es.search(index=data_index, body=body)
            hits = res_kw["hits"]["hits"]

        if not hits:
            return [{"message": f"No records found for: {query}", "query": query}]

        results = []
        for hit in hits:
            src = hit["_source"]
            record = {"_score": hit["_score"], "_id": hit["_id"]}
            for f in [
                "CASENUMBER",
                "ORDER__C",
                "STATUS",
                "TYPE",
                "PRIORITY",
                "SERIAL_NUMBER__C",
                "MODEL_NUMBER__C",
                "CERTIFICATE_NO__C",
                "ACCOUNT_NAME_TEXT_ONLY__C",
                "ACCOUNT_MANAGER__C",
                "CONTACTEMAIL",
                "CONTACT_EMAIL__C",
                "CONTACTPHONE",
                "CONTACT_PHONE__C",
                "CONTACTMOBILE",
                "REGION__C",
                "CASE_ACCOUNT_REGION__C",
                "SUBJECT",
                "DESCRIPTION",
                "CASE_RESOLUTION__C",
                "CLOSEDDATE",
                "CREATEDDATE",
                "ISCLOSED",
                "SLA_MET__C",
                "ORDER_AMOUNT_USD__C",
                "PURCHASE_ORDER__C",
                "QUOTE__C",
                "TITLE",
                "PRODUCT_TITLE",
                "PRODUCT_DESCRIPTION",
                "AEM_PROD_DESC",
                "DOC_TYPE",
                "ADDRESSDETAILS__C",
                "BUSINESS_GROUP__C",
                "CASE_CHANNEL__C",
                "FE_NAME__C",
                "CONTACT_NAME_TEXT_ONLY__C",
            ]:
                val = src.get(f)
                if val and str(val).strip():
                    record[f] = val
            results.append(record)

        return results

    except Exception as e:
        log.error("elasticsearch.keyword_search.error", error=str(e))
        return [{"error": str(e), "query": query}]


@tool
def elasticsearch_semantic_search(query: str, top_k: int = 5) -> list:
    """
    Search indexed product documentation, manuals, and knowledge articles
    using BGE-M3 semantic embeddings. Use this for: product questions,
    how-to guides, technical documentation, pricing, specifications.
    Do NOT use for order/case/serial number lookups — use elasticsearch_keyword_search instead.
    """
    log.info("elasticsearch.semantic_search", query=query, top_k=top_k)

    # First try vector store
    store = _get_vector_store()
    if store is not None:
        try:
            docs = store.similarity_search(query, k=top_k)
            if docs:
                return [
                    {
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "title": doc.metadata.get("title", ""),
                        "retrieval_method": "BGE-M3 kNN",
                    }
                    for doc in docs
                ]
        except Exception as e:
            log.warning("elasticsearch.semantic_search.vector_failed", error=str(e))

    # Fallback: keyword search on product/doc fields in main index
    try:
        from app.config import settings
        es = _get_es_client()
        data_index = getattr(settings, "es_data_index", "next_elastic_test1")

        body = {
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["TITLE^3", "PRODUCT_TITLE^3", "PRODUCT_DESCRIPTION^2",
                               "DESCRIPTION", "AEM_PROD_DESC", "KEYWORDS"],
                    "type": "best_fields",
                }
            },
        }
        res = es.search(index=data_index, body=body)
        hits = res["hits"]["hits"]
        if hits:
            return [
                {
                    "content": h["_source"].get("PRODUCT_DESCRIPTION") or
                               h["_source"].get("DESCRIPTION") or
                               h["_source"].get("AEM_PROD_DESC", ""),
                    "title": h["_source"].get("PRODUCT_TITLE") or h["_source"].get("TITLE", ""),
                    "source": "elasticsearch",
                    "retrieval_method": "keyword fallback",
                }
                for h in hits
            ]
    except Exception as e:
        log.error("elasticsearch.semantic_search.fallback_error", error=str(e))

    return [{"message": f"No documentation found for: {query}"}]


@tool
def elasticsearch_ingest_document(title: str, content: str, source: str = "manual") -> dict:
    """
    Index a new document into Elasticsearch using BGE-M3 embeddings.
    Use when the user wants to add a new knowledge article, guide, policy, or FAQ.
    """
    log.info("elasticsearch.ingest", title=title, source=source)
    store = _get_vector_store()
    if store is None:
        return {"error": "Elasticsearch not available.", "indexed": False}
    try:
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.create_documents(
            [content], metadatas=[{"title": title, "source": source}]
        )
        store.add_documents(chunks)
        return {"indexed": True, "title": title, "chunks_stored": len(chunks)}
    except Exception as e:
        log.error("elasticsearch.ingest.error", error=str(e))
        return {"error": str(e), "indexed": False}
