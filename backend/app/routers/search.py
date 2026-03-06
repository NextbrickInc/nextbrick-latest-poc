# backend/app/routers/search.py
# ─────────────────────────────────────────────────────────────────────────────
# POST /api/search — Faceted search for both Support and Main Site pages.
# Returns results, facets, and optionally a generated AI answer.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
import structlog
from fastapi import APIRouter, status

from app.models.search import SearchRequest, SearchResponse
from app.services.search_service import execute_search
from app.services.cache_service import cache
from app.services.generated_answer_service import generate_answer

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search(req: SearchRequest) -> SearchResponse:
    """Execute a faceted search with optional AI-generated answer."""

    # Check cache first
    filters_hash = hashlib.md5(json.dumps(req.filters, sort_keys=True).encode()).hexdigest()[:8]
    cached = cache.get_search(req.query, req.page_type, filters_hash, req.page)
    if cached:
        log.info("search.cache_hit", query=req.query[:50])
        return SearchResponse(**cached)

    # Execute search
    response = execute_search(req)

    # Generate AI answer if requested and we have results
    if req.include_generated_answer and response.results and req.page == 1:
        try:
            answer = generate_answer(req.query, response.results, req.language or "en")
            if answer:
                response.generated_answer = answer
        except Exception as e:
            log.warning("search.generated_answer_failed", error=str(e))

    # Cache the response
    cache.put_search(req.query, req.page_type, filters_hash, req.page, response.model_dump())

    return response
