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
from app.schemas.support import (
    CreateReleaseRequest,
    ReleaseNoteOut,
    ReplyRequest,
    SetTicketStatusRequest,
    TicketOut,
)
from app.services import platform_service, support_service

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


# --- Support (tickets cross-tenant) -----------------------------------------


@router.get("/tickets", response_model=ListResponse[TicketOut])
async def list_tickets(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: PlatformContext = Depends(require_platform_scope("tickets")),
) -> ListResponse[TicketOut]:
    items = await support_service.list_all_tickets(session, status=status)
    return ListResponse(items=items, total=len(items))


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_db),
    _: PlatformContext = Depends(require_platform_scope("tickets")),
) -> TicketOut:
    ticket = await support_service.get_ticket_platform(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket


@router.post("/tickets/{ticket_id}/reply", response_model=TicketOut)
async def reply_ticket(
    ticket_id: int,
    body: ReplyRequest,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("tickets")),
) -> TicketOut:
    ticket = await support_service.platform_reply(session, ticket_id, admin.user_id, body.body)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket


@router.post("/tickets/{ticket_id}/status", response_model=TicketOut)
async def set_ticket_status(
    ticket_id: int,
    body: SetTicketStatusRequest,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("tickets")),
) -> TicketOut:
    try:
        ticket = await support_service.set_ticket_status(
            session, ticket_id, admin.user_id, body.status
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket


# --- Notes de version (changelog produit) -----------------------------------


@router.get("/releases", response_model=ListResponse[ReleaseNoteOut])
async def list_releases(
    session: AsyncSession = Depends(get_db),
    _: PlatformContext = Depends(require_platform_scope("clients:read")),
) -> ListResponse[ReleaseNoteOut]:
    items = await support_service.list_all_releases(session)
    return ListResponse(items=items, total=len(items))


@router.post("/releases", response_model=ReleaseNoteOut, status_code=201)
async def create_release(
    body: CreateReleaseRequest,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("*")),
) -> ReleaseNoteOut:
    return await support_service.create_release(
        session,
        admin.user_id,
        version=body.version,
        title=body.title,
        body=body.body,
        category=body.category,
    )


@router.post("/releases/{note_id}/publish", response_model=ReleaseNoteOut)
async def publish_release(
    note_id: int,
    session: AsyncSession = Depends(get_db),
    admin: PlatformContext = Depends(require_platform_scope("*")),
) -> ReleaseNoteOut:
    note = await support_service.publish_release(session, note_id, admin.user_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note introuvable")
    return note
