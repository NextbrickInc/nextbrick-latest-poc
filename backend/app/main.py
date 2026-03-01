# backend/app/main.py
# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application factory.
# Assembles middleware, routers, and lifespan events.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from contextlib import asynccontextmanager
import structlog
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import health as health_router
from app.routers import chat as chat_router

# ── Logging setup ─────────────────────────────────────────────────────────────
def _configure_logging() -> None:
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log = structlog.get_logger("startup")
    log.info(
        "server.start",
        app=settings.app_name,
        version=settings.app_version,
        model=settings.effective_model_name,
        model_url=settings.effective_model_url,
    )
    yield
    log.info("server.shutdown")


# ── Factory function ──────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    _configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Nextbrick Agentic AI POC Backend",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS — allow Vite dev server and configured frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structured request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Routers
    app.include_router(health_router.router)
    app.include_router(chat_router.router)

    return app


# ── Module-level instance used by uvicorn ────────────────────────────────────
app = create_app()
