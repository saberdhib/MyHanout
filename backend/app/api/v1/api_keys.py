"""Endpoints clés API (accès programmatique). Gestion réservée au propriétaire.

La clé en clair n'est renvoyée QU'À la création. Ensuite, seul le préfixe est visible.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser, generate_api_key
from app.models.api_key import ApiKey
from app.schemas.common import ListResponse
from app.schemas.integrations import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["integrations"])


def _require_owner(user: CurrentUser) -> None:
    if user.role != "owner":
        raise PermissionDeniedError("Seul le propriétaire gère les clés API")


def _out(k: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=k.id,
        name=k.name,
        prefix=k.prefix,
        scopes=k.scopes,
        revoked=k.revoked,
        last_used_at=k.last_used_at,
        created_at=k.created_at,
    )


@router.get("", response_model=ListResponse[ApiKeyOut])
async def list_keys(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ListResponse[ApiKeyOut]:
    _require_owner(user)
    rows = list((await session.scalars(select(ApiKey).order_by(ApiKey.id.desc()))).all())
    return ListResponse(items=[_out(k) for k in rows], total=len(rows))


@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_key(
    body: ApiKeyCreate,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ApiKeyCreated:
    """Crée une clé API. ⚠️ La valeur complète n'est affichée qu'ici."""
    _require_owner(user)
    full, prefix, key_hash = generate_api_key()
    key = ApiKey(
        name=body.name,
        prefix=prefix,
        key_hash=key_hash,
        scopes=body.scopes or "*",
        created_by_user_id=user.id,
    )
    session.add(key)
    await session.flush()
    return ApiKeyCreated(**_out(key).model_dump(), key=full)


@router.delete("/{key_id}", status_code=200)
async def revoke_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Révoque une clé (irréversible ; la clé cesse immédiatement de fonctionner)."""
    _require_owner(user)
    key = await session.get(ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="Clé introuvable")
    key.revoked = True
    await session.flush()
    return {"id": key.id, "revoked": True}
