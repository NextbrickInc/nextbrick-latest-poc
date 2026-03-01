# backend/app/routers/health.py
from fastapi import APIRouter
from app.config import settings
from app.models.chat import HealthResponse
from app.middleware.metrics import metrics_store
from app.models.chat import MetricsResponse

router = APIRouter(prefix="/api", tags=["ops"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Service health check — used by frontend to show model badge."""
    return HealthResponse(
        ok=True,
        model_configured=bool(settings.effective_model_url),
        model_name=settings.effective_model_name,
        model_url=settings.effective_model_url,
        es_host=settings.es_host,
        version=settings.app_version,
    )


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    """In-memory POC metrics used by the frontend comparison panel."""
    return MetricsResponse(
        total_requests=metrics_store.total_requests,
        avg_latency_ms=metrics_store.avg_latency_ms,
        tool_calls_total=metrics_store.total_tool_calls,
        uptime_seconds=metrics_store.uptime_seconds,
    )
