"""Connecteurs par commerce (modèle B, self-service) — owner only.

Le commerçant branche SON WhatsApp/Slack/Telegram : secrets chiffrés, jamais
renvoyés. `GET` ne montre que l'état + les champs publics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security import CurrentUser
from app.services import connector_service

router = APIRouter(prefix="/connectors", tags=["connectors"])


def _require_owner(user: CurrentUser) -> None:
    if user.role != "owner":
        raise PermissionDeniedError("Réservé au propriétaire du commerce.")


class ConnectorStatus(BaseModel):
    kind: str
    configured: bool
    active: bool
    public: dict
    has_secret: bool


class ConnectorUpsert(BaseModel):
    # Champs libres (publics + secrets) ; les secrets vides ne touchent pas l'existant.
    fields: dict
    active: bool = True


@router.get("/manage", response_model=list[ConnectorStatus])
async def list_manage(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[ConnectorStatus]:
    """État des connecteurs du commerce (sans secret)."""
    _require_owner(user)
    return [ConnectorStatus(**s) for s in await connector_service.status(session)]


@router.put("/manage/{kind}", response_model=ConnectorStatus)
async def upsert_connector(
    kind: str,
    body: ConnectorUpsert,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ConnectorStatus:
    """Enregistre/maj les identifiants d'un connecteur (secrets chiffrés)."""
    _require_owner(user)
    if kind not in connector_service.KINDS:
        raise NotFoundError(f"Connecteur inconnu : {kind}")
    fields = {**body.fields, "active": body.active}
    await connector_service.upsert(session, kind, fields)
    await session.commit()
    for s in await connector_service.status(session):
        if s["kind"] == kind:
            return ConnectorStatus(**s)
    raise NotFoundError(kind)


@router.delete("/manage/{kind}", status_code=204)
async def delete_connector(
    kind: str,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Débranche un connecteur (supprime ses identifiants)."""
    _require_owner(user)
    ok = await connector_service.delete(session, kind)
    if not ok:
        raise NotFoundError(f"Connecteur {kind} introuvable")
    await session.commit()
