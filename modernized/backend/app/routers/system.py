"""System endpoints — health/readiness plus the modernized CODATE01 inquiry."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request

from ..models import HealthStatus

router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthStatus)
def health(request: Request):
    store = request.app.state.store
    return HealthStatus(status="ok", version="1.0.0", seeded=store.seeded,
                        time=datetime.now(timezone.utc))


@router.get("/api/system/date")
def system_date():
    """Modernized CODATE01 (CDRD) — system date inquiry."""
    now = datetime.now(timezone.utc)
    return {"date": now.strftime("%Y-%m-%d"), "iso": now.isoformat()}
