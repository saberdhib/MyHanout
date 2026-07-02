"""Backoffice plateforme (MyHanout) — pilotage cross-tenant du parc clients.

⚠️ Toutes les routes exigent un `PlatformAdmin` actif (`require_platform_scope`) et
sont **auditées**. C'est l'inverse du garde-fou tenant : un opérateur voit tous les
commerces. Réservé à l'équipe MyHanout, jamais exposé aux commerçants.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.platform_auth import PlatformContext, require_platform_scope
from app.schemas.common import ListResponse
from app.schemas.platform import (
    ClientDetail,
    ClientSummary,
    PlatformOverview,
    ProvisionClientRequest,
    SetPlanRequest,
    SetStatusRequest,
)
from app.services import platform_service

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/overview", response_model=PlatformOverview)
async def get_overview(
    session: AsyncSession = Depends(get_db),
    _: PlatformContext = Depends(require_platform_scope("clients:read")),
) -> PlatformOverview:
    return await platform_service.overview(session)


@router.get("/clients", response_model=ListResponse[ClientSummary])
async def get_clients(
    session: AsyncSession = Depends(get_db),
    _: PlatformContext = Depends(require_platform_scope("clients:read")),
) -> ListResponse[ClientSummary]:
    items = await platform_service.list_clients(session)
    return ListResponse(items=items, total=len(items))


@router.get("/clients/{org_id}", response_model=ClientDetail)
async def get_client(
    org_id: int,
    session: AsyncSession = Depends(get_db),
    _: PlatformContext = Depends(require_platform_scope("clients:read")),
) -> ClientDetail:
    detail = await platform_service.client_detail(session, org_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Commerce introuvable")
    return detail


@router.post("/clients", response_model=ClientDetail, status_code=201)
async def provision_client(
    body: ProvisionClientRequest,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("*")),
) -> ClientDetail:
    """Provisionne un nouveau commerce (org + owner + abonnement). Superadmin only."""
    try:
        org = await platform_service.provision_client(
            session,
            admin.user_id,
            name=body.name,
            slug=body.slug,
            business_type=body.business_type,
            owner_email=body.owner_email,
            owner_full_name=body.owner_full_name,
            owner_password=body.owner_password,
            plan=body.plan,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    detail = await platform_service.client_detail(session, org.id)
    assert detail is not None
    return detail


@router.post("/clients/{org_id}/status", response_model=ClientDetail)
async def set_status(
    org_id: int,
    body: SetStatusRequest,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("*")),
) -> ClientDetail:
    """Suspend / réactive / résilie un commerce (contrôle d'accès). Superadmin only."""
    try:
        org = await platform_service.set_org_status(
            session, admin.user_id, org_id, body.status, body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if org is None:
        raise HTTPException(status_code=404, detail="Commerce introuvable")
    detail = await platform_service.client_detail(session, org_id)
    assert detail is not None
    return detail


@router.post("/clients/{org_id}/plan", response_model=ClientDetail)
async def set_plan(
    org_id: int,
    body: SetPlanRequest,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("billing")),
) -> ClientDetail:
    """Met à jour l'abonnement (plan/MRR/statut). Scope `billing`."""
    try:
        sub = await platform_service.set_plan(
            session,
            admin.user_id,
            org_id,
            plan=body.plan,
            mrr_eur=body.mrr_eur,
            subscription_status=body.subscription_status,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if sub is None:
        raise HTTPException(status_code=404, detail="Commerce introuvable")
    detail = await platform_service.client_detail(session, org_id)
    assert detail is not None
    return detail
