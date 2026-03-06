# backend/app/tools/elasticsearch_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Fixed: queries next_elastic_test1 (real case/order/product data) using
# both keyword search and semantic search via BGE-M3 embeddings.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from pathlib import Path
import re
import structlog
from typing import Optional, Any
from langchain_core.tools import tool

log = structlog.get_logger(__name__)

_embeddings = None
_vector_store = None
_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
_OFFICIAL_MANUAL_URLS = {
    "u1610a_u1620a handheld digital oscilloscope.pdf": "https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf",
}


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


def _extract_model_tokens(query: str) -> list[str]:
    """Extract probable product model tokens, e.g. U1610A, N9030A, DSOX1202A."""
    if not query:
        return []
    # Keep uppercase model codes with trailing letter optional.
    return re.findall(r"\b[A-Z]{1,4}\d{3,5}[A-Z]?\b", query.upper())


def _local_pdf_fallback_websearch(query: str, size: int, reason: str = "") -> Optional[dict]:
    """
    Fallback for manual lookup when asset index is unavailable.
    Returns websearch-like payload with expected fields in _source:
    TITLE, DESCRIPTION, ASSET_PATH, CONTENT_TYPE_NAME.
    """
    if not _DOCS_DIR.exists():
        return None

    model_tokens = _extract_model_tokens(query)
    query_l = (query or "").lower()

    candidates: list[tuple[int, Path]] = []
    for pdf_path in _DOCS_DIR.glob("*.pdf"):
        name_l = pdf_path.name.lower()
        score = 0

        for model in model_tokens:
            if model.lower() in name_l:
                score += 100

        if "manual" in name_l or "user" in name_l or "guide" in name_l:
            score += 10

        if query_l and any(tok in name_l for tok in query_l.split() if len(tok) >= 5):
            score += 5

        if score > 0:
            candidates.append((score, pdf_path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    top = candidates[: max(1, size)]

    fallback_hits = []
    for score, pdf in top:
        title = pdf.stem
        normalized = re.sub(r"\s+\(\d+\)\.pdf$", ".pdf", pdf.name.strip(), flags=re.IGNORECASE)
        official_url = _OFFICIAL_MANUAL_URLS.get(pdf.name.lower()) or _OFFICIAL_MANUAL_URLS.get(normalized.lower())
        asset_path = official_url or str(pdf)

        description = (
            "Manual found via local docs fallback. "
            "Use ASSET_PATH as the direct manual link; LOCAL_PATH is the local file path."
        )
        if reason:
            description = f"{description} Fallback reason: {reason}"

        fallback_hits.append(
            {
                "_id": f"local-doc:{pdf.name}",
                "_score": float(score),
                "_source": {
                    "TITLE": title,
                    "DESCRIPTION": description,
                    "ASSET_PATH": asset_path,
                    "CONTENT_TYPE_NAME": "PDF",
                    "LOCAL_PATH": str(pdf),
                },
            }
        )

    return {
        "index": "local_docs_fallback",
        "total": len(fallback_hits),
        "hits": fallback_hits,
        "aggregations": {},
    }


def _pick_best_index_for_websearch(es: Any, explicit_index: Optional[str], query: str) -> str:
    """Choose the best index if user does not explicitly provide one."""
    from app.config import settings
    if explicit_index:
        return explicit_index

    query_l = (query or "").lower()
    default_index = getattr(settings, "es_data_index", "next_elastic_test1")

    # Heuristic routing by intent.
    if any(k in query_l for k in ("manual", "datasheet", "pdf", "documentation", "user guide")):
        candidate = "asset_v2"
        try:
            if es.indices.exists(index=candidate):
                return candidate
        except Exception:
            pass

    # Cases, tickets, support records, orders, policy-like content in this project live in data index.
    return default_index


def _build_websearch_body(query: str, size: int, aggs: Optional[dict]) -> dict:
    """
    Build an ES query body supporting:
    - full-text relevance search
    - 'last N documents' style queries
    - monthly sales breakdown (date_histogram + sum)
    - explicit external aggregations via `aggs`
    """
    query_l = (query or "").lower()
    requested_size = max(1, min(size, 100))

    # "show me the last 5 documents" style.
    m_last = re.search(r"\blast\s+(\d{1,3})\b", query_l)
    if m_last:
        requested_size = max(1, min(int(m_last.group(1)), 100))

    body: dict = {
        "size": requested_size,
        "track_total_hits": True,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["*"],
                "type": "best_fields",
            }
        },
    }

    if "last" in query_l and ("document" in query_l or "record" in query_l):
        body["sort"] = [{"CREATEDDATE": {"order": "desc", "unmapped_type": "date"}}]

    # "sales ... break down by month" style analytical query.
    if (
        "sales" in query_l
        and ("break down by month" in query_l or "broken down by month" in query_l or "by month" in query_l)
    ):
        body["size"] = 0
        body["query"] = {"match_all": {}}
        body["aggs"] = {
            "sales_by_month": {
                "date_histogram": {
                    "field": "CREATEDDATE",
                    "calendar_interval": "month",
                    "min_doc_count": 0,
                },
                "aggs": {
                    "sales_total": {
                        "sum": {"field": "ORDER_AMOUNT_USD__C"}
                    }
                },
            }
        }
        return body

    if aggs:
        body["aggs"] = aggs

    return body


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def elasticsearch_keyword_search(query: str, top_k: int = 5, language: str = "en") -> list:
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
                "DESCRIPTION__C",
                "CASE_FIRST_ASSIGNED__C",
                "CASE_OWNER_MANAGER_TEXT__C",
                "DUE_DATE_AND_TIME__C",
                "TIME_REMAINING_ALL__C",
                "TIME_REMAINING_IN_MINUTE__C",
                "CASE_ASSIGNED_TAT_NUMBER__C",
                "OF_DAYS_IN_CURRENT_STAGE__C",
                "ORIGIN",
                "COPIED_FROM_CASE__C",
                "CONTACTFAX",
                "SLA_MET_NOT__C",
                "FIRST_ASSIGNED__C",
                "LASTMODIFIEDDATE",
                "SLA_DUE_DATE__C",
                "PARENTID",
                "LOCATION__C",
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
def elasticsearch_semantic_search(query: str, top_k: int = 5, language: str = "en") -> list:
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


@tool
def elasticsearch_websearch(
    query: str,
    index: Optional[str] = None,
    size: int = 10,
    aggs: Optional[dict] = None,
    language: str = "en",
) -> dict:
    """
    A powerful tool for searching and analysing data within your Elasticsearch cluster.
    It supports both full-text relevance searches and structured analytical queries.

    Use this tool for any query that involves finding documents, counting, aggregating,
    or summarising data from a known index.

    Examples:
    - "find articles about serverless architecture"
    - "search for support tickets mentioning 'billing issue' or 'refund request'"
    - "what is our policy on parental leave?"
    - "list all products where the category is 'electronics'"
    - "show me the last 5 documents from that index"
    - "show me the sales over the last year broken down by month"

    Notes:
    - The `index` parameter can be used to specify which index to search against.
      If not provided, the tool selects the best index heuristically.
    - It is perfectly fine not to specify `index`. Only set it when you already
      know the index and fields you want to search on, e.g. user explicitly specified it.
    """

    log.info("elasticsearch.websearch", query=query, index=index, size=size, lang=language)
    try:
        es = _get_es_client()
        target_index = _pick_best_index_for_websearch(es=es, explicit_index=index, query=query)
        
        # ── Rule 1 & Rule 2: Two-pass language search ────────────────────────
        lang = (language or "en").strip().lower()
        used_fallback = False
        
        lang_title_map = {
            "de": "German", "es": "Spanish", "fr": "French", "zh": "Chinese",
            "zh-hans": "Chinese (Simplified)", "zh-hant": "Chinese (Traditional)",
            "ja": "Japanese", "ko": "Korean", "pt": "Portuguese", "it": "Italian",
        }
        lang_lower = lang.split("-")[0]
        language_filter = lang_title_map.get(lang, lang_title_map.get(lang_lower))

        body = _build_websearch_body(query=query, size=size, aggs=aggs)

        if language_filter and lang not in ("en", "english"):
            # Pass 1: Try user language
            body_p1 = body.copy()
            body_p1["query"] = {
                "bool": {
                    "must": body["query"],
                    "filter": [{"term": {"LANGUAGE_TITLE.keyword": language_filter}}]
                }
            }
            res_p1 = es.search(index=target_index, body=body_p1)
            total_p1 = res_p1.get("hits", {}).get("total", {}).get("value", 0)
            
            if total_p1 > 0:
                res = res_p1
            else:
                # Pass 2: Fallback to English (Rule 2)
                body_p2 = body.copy()
                body_p2["query"] = {
                    "bool": {
                        "must": body["query"],
                        "filter": [{"term": {"LANGUAGE_TITLE.keyword": "English"}}]
                    }
                }
                res = es.search(index=target_index, body=body_p2)
                used_fallback = True
        else:
            res = es.search(index=target_index, body=body)
        hits = res.get("hits", {}).get("hits", [])

        # Special fallback for manual lookup flow when asset_v2 has no data.
        if not hits and target_index == "asset_v2":
            fallback = _local_pdf_fallback_websearch(query=query, size=size, reason="asset_v2 returned 0 hits")
            if fallback:
                return fallback

        return {
            "index": target_index,
            "total": res.get("hits", {}).get("total", {}).get("value", len(hits)),
            "hits": [
                {
                    "_id": h.get("_id"),
                    "_score": h.get("_score"),
                    "_source": h.get("_source", {}),
                }
                for h in hits
            ],
            "aggregations": res.get("aggregations", {}),
        }
    except Exception as e:
        log.error("elasticsearch.websearch.error", error=str(e))
        if (index or "").lower() == "asset_v2":
            fallback = _local_pdf_fallback_websearch(query=query, size=size, reason=str(e))
            if fallback:
                return fallback
        return {"error": str(e), "query": query}
