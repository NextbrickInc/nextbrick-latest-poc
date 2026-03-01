# backend/run.py
# ─────────────────────────────────────────────────────────────────────────────
# Production Uvicorn entrypoint.
# Usage:
#   Development:  uvicorn app.main:app --reload --port 8000
#   Production:   python run.py
# ─────────────────────────────────────────────────────────────────────────────
import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=False,   # handled by our structlog middleware
    )
