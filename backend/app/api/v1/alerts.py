"""Endpoints alertes décisionnelles : liste + résolution humaine (auditée)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.dataplatform import AlertOut, ResolveAlertRequest
from app.services.alert_service import list_alerts, resolve_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _out(a) -> AlertOut:
    return AlertOut(
        id=a.id,
        kind=str(a.kind),
        priority=str(a.priority),
        status=str(a.status),
        title=a.title,
        message=a.message,
        rule=a.rule,
        threshold=a.threshold,
        observed_value=a.observed_value,
        recommended_action=a.recommended_action,
        explanation=a.explanation,
        entity_type=a.entity_type,
        entity_id=a.entity_id,
        created_at=a.created_at,
    )


@router.get("", response_model=ListResponse[AlertOut])
async def get_alerts(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ListResponse[AlertOut]:
    rows = await list_alerts(session, status=status)
    items = [_out(a) for a in rows]
    return ListResponse(items=items, total=len(items))


@router.post("/{alert_id}/resolve", response_model=AlertOut)
async def resolve(
    alert_id: int,
    body: ResolveAlertRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("orders")),
) -> AlertOut:
    """Résolution humaine (human-in-the-loop) : resolved | dismissed (faux positif)."""
    alert = await resolve_alert(
        session, alert_id, user_id=user.id, note=body.note, dismiss=body.dismiss
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerte introuvable")
    return _out(alert)
