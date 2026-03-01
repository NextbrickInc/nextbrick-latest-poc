# backend/app/middleware/logging.py
# ─────────────────────────────────────────────────────────────────────────────
# Structured request/response logging middleware using structlog.
# Logs: method, path, status_code, duration_ms, request_id (UUID per request).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        bound = log.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        bound.info("request.start")

        try:
            response = await call_next(request)
        except Exception as exc:
            bound.exception("request.error", error=str(exc))
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        bound.info(
            "request.complete",
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Duration-Ms"] = str(duration_ms)
        return response
