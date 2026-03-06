# backend/app/services/search_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Faceted search against Elasticsearch for both Support and Main Site pages.
# Returns results with aggregation buckets formatted as SearchFacet objects.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import time
import structlog
from typing import Any, Optional

from app.config import settings
from app.models.search import (
    SearchRequest, SearchResponse, SearchResult,
    SearchFacet, FacetValue,
)

log = structlog.get_logger(__name__)


_es_client = None

def _get_es_client():
    global _es_client
    if _es_client is not None:
        return _es_client
    from elasticsearch import Elasticsearch
    kwargs = {
        "hosts": [settings.es_host],
        "connections_per_node": 5,
        "http_compress": True,
        "request_timeout": 8,
    }
    if settings.es_username and settings.es_password:
        kwargs["basic_auth"] = (settings.es_username, settings.es_password)
    _es_client = Elasticsearch(**kwargs)
    return _es_client


# ── Index selection per page type ───────────────────────────────────────────

_SUPPORT_INDICES = "asset_v2,next_elastic_test1"
_MAIN_SITE_INDICES = "asset_v2,next_elastic_test1"

# Fields to search per page type
_SUPPORT_FIELDS = [
    "TITLE^4", "PRODUCT_TITLE^3", "DESCRIPTION^2", "PRODUCT_DESCRIPTION^2",
    "CONTENT_TYPE_NAME^2", "KEYWORDS", "AEM_PROD_DESC", "CASENUMBER^5",
    "ORDER__C^5", "SUBJECT^2",
]

_MAIN_SITE_FIELDS = [
    "TITLE^5", "PRODUCT_TITLE^4", "PRODUCT_DESCRIPTION^3", "DESCRIPTION^2",
    "KEYWORDS^2", "AEM_PROD_DESC", "CONTENT_TYPE_NAME",
]

# Aggregation fields per page type
_SUPPORT_AGGS = {
    "product_category": {
        "terms": {"field": "BUSINESS_GROUP__C.keyword", "size": 10, "min_doc_count": 1}
    },
    "content_type": {
        "terms": {"field": "CONTENT_TYPE_NAME.keyword", "size": 10, "min_doc_count": 1}
    },
    "product_suite": {
        "terms": {"field": "PRODUCT_TITLE.keyword", "size": 10, "min_doc_count": 1}
    },
}

_MAIN_SITE_AGGS = {
    "product_area": {
        "terms": {"field": "BUSINESS_GROUP__C.keyword", "size": 8, "min_doc_count": 1}
    },
    "content_type": {
        "terms": {"field": "CONTENT_TYPE_NAME.keyword", "size": 8, "min_doc_count": 1}
    },
}


def _build_query(req: SearchRequest, language_filter: Optional[str] = None) -> dict:
    """Build an ES query body with aggregations for faceted search.

    language_filter: if set, adds a filter on LANGUAGE_TITLE to restrict to this language.
    """
    page_type = req.page_type
    fields = _SUPPORT_FIELDS if page_type == "support" else _MAIN_SITE_FIELDS
    aggs = _SUPPORT_AGGS if page_type == "support" else _MAIN_SITE_AGGS

    # Base query
    must_clause: list[dict] = [
        {
            "multi_match": {
                "query": req.query,
                "fields": fields,
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        }
    ]

    # Tab filtering for main site
    if req.tab and req.tab.lower() != "all":
        tab_map = {
            "solutions": ["Solution", "Application"],
            "learn": ["Training", "Tutorial", "Webinar", "White Paper", "Application Note"],
            "support": ["Manual", "Datasheet", "FAQ", "Knowledge Base", "Troubleshooting"],
            "hardware": ["Hardware", "Instrument", "Module"],
            "software": ["Software", "License", "Download"],
            "product help": ["Manual", "User Guide", "Help", "FAQ"],
        }
        tab_terms = tab_map.get(req.tab.lower(), [req.tab])
        must_clause.append({
            "terms": {"CONTENT_TYPE_NAME.keyword": tab_terms}
        })

    # Apply user-selected filters
    filter_clauses: list[dict] = []
    field_mapping = {
        "product_category": "BUSINESS_GROUP__C.keyword",
        "content_type": "CONTENT_TYPE_NAME.keyword",
        "product_suite": "PRODUCT_TITLE.keyword",
        "product_area": "BUSINESS_GROUP__C.keyword",
    }
    for facet_name, selected_values in req.filters.items():
        if selected_values:
            es_field = field_mapping.get(facet_name, f"{facet_name}.keyword")
            filter_clauses.append({"terms": {es_field: selected_values}})

    # Rule 1 / Rule 2: Language filter on LANGUAGE_TITLE field
    if language_filter:
        filter_clauses.append({"term": {"LANGUAGE_TITLE.keyword": language_filter}})

    # Sort
    sort_clause = []
    if req.sort_by == "date":
        sort_clause = [{"CREATEDDATE": {"order": "desc", "unmapped_type": "date"}}]

    body: dict[str, Any] = {
        "size": req.page_size,
        "from": (req.page - 1) * req.page_size,
        "track_total_hits": True,
        "query": {
            "bool": {
                "must": must_clause,
                **(({"filter": filter_clauses}) if filter_clauses else {}),
            }
        },
        "aggs": aggs,
    }

    if sort_clause:
        body["sort"] = sort_clause

    return body


def _parse_hit(hit: dict) -> SearchResult:
    """Convert an ES hit into a SearchResult."""
    src = hit.get("_source", {})
    title = (
        src.get("TITLE") or src.get("PRODUCT_TITLE") or src.get("SUBJECT") or src.get("CASENUMBER") or ""
    )
    description = (
        src.get("DESCRIPTION") or src.get("PRODUCT_DESCRIPTION") or src.get("AEM_PROD_DESC") or ""
    )
    # Truncate long descriptions
    if len(description) > 300:
        description = description[:297] + "..."

    url = src.get("ASSET_PATH") or src.get("URL") or None
    date = src.get("CREATEDDATE") or src.get("LASTMODIFIEDDATE") or None
    if date and "T" in str(date):
        date = str(date)[:10]  # ISO date only

    return SearchResult(
        id=hit.get("_id", ""),
        title=title,
        description=description,
        category=src.get("BUSINESS_GROUP__C") or src.get("CONTENT_TYPE_NAME") or None,
        date=date,
        url=url,
        image_url=src.get("IMAGE_URL") or None,
        content_type=src.get("CONTENT_TYPE_NAME") or src.get("DOC_TYPE") or None,
        product_area=src.get("BUSINESS_GROUP__C") or None,
        score=hit.get("_score", 0.0) or 0.0,
        source_index=hit.get("_index") or None,
    )


def _parse_aggs(raw_aggs: dict, req: SearchRequest) -> list[SearchFacet]:
    """Convert ES aggregation buckets into SearchFacet objects."""
    facets = []
    display_names = {
        "product_category": "Product Category",
        "content_type": "Content Type",
        "product_suite": "Product Suite",
        "product_area": "Product Areas",
    }

    for agg_name, agg_data in raw_aggs.items():
        buckets = agg_data.get("buckets", [])
        if not buckets:
            continue
        selected_values = req.filters.get(agg_name, [])
        values = [
            FacetValue(
                label=b["key"],
                count=b["doc_count"],
                selected=b["key"] in selected_values,
            )
            for b in buckets
            if b.get("key") and b.get("doc_count", 0) > 0
        ]
        if values:
            facets.append(SearchFacet(
                name=agg_name,
                display_name=display_names.get(agg_name, agg_name.replace("_", " ").title()),
                values=values,
            ))
    return facets


# ── Public API ──────────────────────────────────────────────────────────────

def execute_search(req: SearchRequest) -> SearchResponse:
    """Execute a faceted search against Elasticsearch."""
    started = time.perf_counter()

    try:
        es = _get_es_client()
        indices = _SUPPORT_INDICES if req.page_type == "support" else _MAIN_SITE_INDICES

        # Check which indices exist
        available = []
        for idx in indices.split(","):
            try:
                if es.indices.exists(index=idx.strip()):
                    available.append(idx.strip())
            except Exception:
                pass
        if not available:
            available = [settings.es_data_index]

        index_str = ",".join(available)

        # ── Rule 1 & Rule 2: Two-pass language search ────────────────────────
        # Rule 1: If user's language has content → use it.
        # Rule 2: If not → fall back to English, respond in user's language.
        lang = (req.language or "en").strip().lower()
        language_filter = None
        used_fallback = False

        if lang not in ("en", "english"):
            # Map language codes to LANGUAGE_TITLE values in ES
            lang_title_map = {
                "de": "German",
                "es": "Spanish",
                "fr": "French",
                "zh": "Chinese",
                "zh-hans": "Chinese (Simplified)",
                "zh-hant": "Chinese (Traditional)",
                "ja": "Japanese",
                "ko": "Korean",
                "pt": "Portuguese",
                "it": "Italian",
            }
            lang_lower = lang.split("-")[0]  # e.g. "zh-hans" -> "zh"
            language_filter = lang_title_map.get(lang, lang_title_map.get(lang_lower))

            if language_filter:
                # Pass 1: Try user language
                body_pass1 = _build_query(req, language_filter=language_filter)
                log.info("search_service.pass1", lang=language_filter, query=req.query[:50])
                raw_pass1 = es.search(index=index_str, body=body_pass1)
                total_hits_p1 = raw_pass1.get("hits", {}).get("total", {})
                total_p1 = total_hits_p1.get("value", 0) if isinstance(total_hits_p1, dict) else int(total_hits_p1 or 0)

                if total_p1 > 0:
                    raw = raw_pass1
                    log.info("search_service.rule1_hit", count=total_p1)
                else:
                    # Pass 2: Fall back to English (Rule 2)
                    body_pass2 = _build_query(req, language_filter="English")
                    log.info("search_service.rule2_fallback", query=req.query[:50])
                    raw = es.search(index=index_str, body=body_pass2)
                    used_fallback = True
            else:
                body = _build_query(req)
                raw = es.search(index=index_str, body=body)
        else:
            body = _build_query(req)
            raw = es.search(index=index_str, body=body)

        log.info("search_service.execute", index=index_str, query=req.query[:50], page=req.page, lang=lang, fallback=used_fallback)

        total_hits = raw.get("hits", {}).get("total", {})
        total = total_hits.get("value", 0) if isinstance(total_hits, dict) else int(total_hits or 0)

        results = [_parse_hit(h) for h in raw.get("hits", {}).get("hits", [])]
        facets = _parse_aggs(raw.get("aggregations", {}), req)

        # Tab counts — run a terms agg on content_type for tab breakdown
        tab_counts = {}
        if req.page_type == "main_site":
            content_type_agg = raw.get("aggregations", {}).get("content_type", {})
            for bucket in content_type_agg.get("buckets", []):
                tab_counts[bucket["key"]] = bucket["doc_count"]
            tab_counts["All"] = total

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return SearchResponse(
            query=req.query,
            total=total,
            results=results,
            facets=facets,
            tab_counts=tab_counts,
            page=req.page,
            page_size=req.page_size,
            latency_ms=elapsed_ms,
            generated_answer=None,  # Set by router if requested
        )

    except Exception as e:
        log.error("search_service.error", error=str(e), query=req.query[:50])
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return SearchResponse(
            query=req.query,
            total=0,
            results=[],
            facets=[],
            page=req.page,
            page_size=req.page_size,
            latency_ms=elapsed_ms,
        )
