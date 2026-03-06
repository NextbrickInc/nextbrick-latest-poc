# backend/app/routers/user.py
# ─────────────────────────────────────────────────────────────────────────────
# /api/user — User profile preferences and satisfaction feedback endpoints.
# In-memory store (replace with DB persistence in production).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import time
import structlog
from typing import Optional, List
from fastapi import APIRouter, status
from pydantic import BaseModel

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/user", tags=["user"])

# ── In-memory stores ─────────────────────────────────────────────────────────
_profiles: dict[str, dict] = {}
_feedback: list[dict] = []


# ── Models ───────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    user_id: str
    language: str = "en"
    role: Optional[str] = None          # e.g. "Engineer", "Sales", "Manager"
    interests: List[str] = []           # e.g. ["oscilloscopes", "software"]
    preferred_content_types: List[str] = []


class FeedbackSignal(BaseModel):
    user_id: str
    message_id: Optional[str] = None   # chat session / message identifier
    query: Optional[str] = None
    response_snippet: Optional[str] = None
    signal: str                         # "thumbs_up" | "thumbs_down"
    comment: Optional[str] = None


class ProfileResponse(BaseModel):
    user_id: str
    profile: dict
    ok: bool = True


class FeedbackResponse(BaseModel):
    ok: bool = True
    total_feedback: int = 0


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/profile/{user_id}", status_code=status.HTTP_200_OK)
def get_profile(user_id: str) -> ProfileResponse:
    """Retrieve the saved user profile (or sensible defaults)."""
    profile = _profiles.get(user_id, {
        "user_id": user_id,
        "language": "en",
        "role": None,
        "interests": [],
        "preferred_content_types": [],
    })
    return ProfileResponse(user_id=user_id, profile=profile)


@router.post("/profile", status_code=status.HTTP_200_OK)
def save_profile(req: UserProfile) -> ProfileResponse:
    """Save or update user profile preferences."""
    _profiles[req.user_id] = req.model_dump()
    log.info("user.profile_saved", user_id=req.user_id, lang=req.language)
    return ProfileResponse(user_id=req.user_id, profile=_profiles[req.user_id])


@router.post("/feedback", status_code=status.HTTP_200_OK)
def submit_feedback(req: FeedbackSignal) -> FeedbackResponse:
    """Log a thumbs-up or thumbs-down satisfaction signal."""
    _feedback.append({
        **req.model_dump(),
        "ts": time.time(),
    })
    log.info(
        "user.feedback",
        user_id=req.user_id,
        signal=req.signal,
        query=(req.query or "")[:80],
    )
    return FeedbackResponse(ok=True, total_feedback=len(_feedback))


@router.get("/feedback/summary", status_code=status.HTTP_200_OK)
def feedback_summary() -> dict:
    """Return a simple aggregate of feedback signals."""
    up = sum(1 for f in _feedback if f["signal"] == "thumbs_up")
    down = sum(1 for f in _feedback if f["signal"] == "thumbs_down")
    return {
        "total": len(_feedback),
        "thumbs_up": up,
        "thumbs_down": down,
        "satisfaction_rate": round(up / max(len(_feedback), 1) * 100, 1),
    }
