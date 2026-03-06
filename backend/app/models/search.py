# backend/app/models/search.py
# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models for the faceted search API.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1024)
    page_type: Literal["support", "main_site"] = "support"
    filters: dict[str, list[str]] = Field(default_factory=dict)
    sort_by: Literal["relevance", "date"] = "relevance"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    language: Optional[str] = None
    tab: Optional[str] = None  # e.g., "Solutions", "Learn", "Support", "All", "Hardware", "Software"
    include_generated_answer: bool = True


class SearchResult(BaseModel):
    id: str
    title: str = ""
    description: str = ""
    category: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    content_type: Optional[str] = None
    product_area: Optional[str] = None
    score: float = 0.0
    source_index: Optional[str] = None


class FacetValue(BaseModel):
    label: str
    count: int
    selected: bool = False


class SearchFacet(BaseModel):
    name: str
    display_name: str = ""
    values: list[FacetValue] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    total: int = 0
    results: list[SearchResult] = Field(default_factory=list)
    facets: list[SearchFacet] = Field(default_factory=list)
    tab_counts: dict[str, int] = Field(default_factory=dict)
    page: int = 1
    page_size: int = 10
    latency_ms: int = 0
    generated_answer: Optional[str] = None
