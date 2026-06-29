"""Endpoints d'import générique (JSON) + synchronisation entrepôt de données."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser
from app.ingestion.dwh import DwhSyncResult
from app.services.import_service import (
    ImportPayload,
    ImportResult,
    import_json,
    sync_to_dwh,
)
from app.services.pos_service import POSSyncResult, sync_from_connector

router = APIRouter(prefix="/import", tags=["import"])


def _org(user: CurrentUser) -> int:
    if user.organization_id is None:
        raise PermissionDeniedError("Aucune organisation active")
    return user.organization_id


@router.post("/json", response_model=ImportResult)
async def import_json_endpoint(
    payload: ImportPayload,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> ImportResult:
    """Importe fournisseurs/produits/stock/ventes depuis un export JSON (idempotent)."""
    return await import_json(session, payload=payload, user_id=user.id)


@router.post("/dwh/sync", response_model=DwhSyncResult)
async def dwh_sync_endpoint(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> DwhSyncResult:
    """Pousse un snapshot (catalogue/stock/ventes) vers l'entrepôt de données configuré."""
    return await sync_to_dwh(session, organization_id=_org(user), user_id=user.id)


@router.post("/pos/sync", response_model=POSSyncResult)
async def pos_sync_endpoint(
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> POSSyncResult:
    """Ingère les ventes depuis la caisse (mock keyless ou caisse réelle), idempotent."""
    return await sync_from_connector(session, user_id=user.id, limit=limit)
