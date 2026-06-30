"""Endpoints webhooks sortants (n8n / Make / Zapier). Gestion réservée au propriétaire.

Le secret de signature n'est renvoyé QU'À la création.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser
from app.models.webhook import WebhookEndpoint
from app.schemas.common import ListResponse
from app.schemas.integrations import WebhookCreate, WebhookCreated, WebhookOut
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["integrations"])


def _require_owner(user: CurrentUser) -> None:
    if user.role != "owner":
        raise PermissionDeniedError("Seul le propriétaire gère les webhooks")


def _out(w: WebhookEndpoint) -> WebhookOut:
    return WebhookOut(
        id=w.id,
        url=w.url,
        events=w.events,
        active=w.active,
        last_status=w.last_status,
        last_delivered_at=w.last_delivered_at,
        failures=w.failures,
        created_at=w.created_at,
    )


@router.get("", response_model=ListResponse[WebhookOut])
async def list_webhooks(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ListResponse[WebhookOut]:
    _require_owner(user)
    rows = list(
        (await session.scalars(select(WebhookEndpoint).order_by(WebhookEndpoint.id.desc()))).all()
    )
    return ListResponse(items=[_out(w) for w in rows], total=len(rows))


@router.post("", response_model=WebhookCreated, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> WebhookCreated:
    """Enregistre une URL (n8n/Make/Zapier). Le secret HMAC est montré une fois."""
    _require_owner(user)
    secret = body.secret or webhook_service.new_secret()
    wh = WebhookEndpoint(
        url=body.url,
        secret=secret,
        events=body.events or "*",
        created_by_user_id=user.id,
    )
    session.add(wh)
    await session.flush()
    return WebhookCreated(**_out(wh).model_dump(), secret=secret)


@router.delete("/{webhook_id}", status_code=200)
async def delete_webhook(
    webhook_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    _require_owner(user)
    wh = await session.get(WebhookEndpoint, webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook introuvable")
    await session.delete(wh)
    await session.flush()
    return {"id": webhook_id, "deleted": True}
