"""Endpoints Support (côté commerçant) + changelog produit.

Le commerçant ouvre/consulte SES tickets (garde-fou tenant) et lit les notes de version
publiées par MyHanout. Le traitement des tickets côté opérateur est dans `api/v1/platform.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.support import (
    CreateTicketRequest,
    ReleaseNoteOut,
    ReplyRequest,
    TicketOut,
)
from app.services import support_service

router = APIRouter(tags=["support"])


@router.get("/support/tickets", response_model=ListResponse[TicketOut])
async def list_my_tickets(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> ListResponse[TicketOut]:
    rows = await support_service.list_tickets(session, status=status)
    # Les listes ne chargent pas les messages (relation) : vue résumée.
    items = [
        TicketOut(
            id=t.id,
            subject=t.subject,
            category=t.category,
            status=str(t.status),
            priority=str(t.priority),
            created_by_user_id=t.created_by_user_id,
            assigned_admin_id=t.assigned_admin_id,
            created_at=t.created_at.isoformat() if t.created_at else None,
            updated_at=t.updated_at.isoformat() if t.updated_at else None,
            organization_id=t.organization_id,
        )
        for t in rows
    ]
    return ListResponse(items=items, total=len(items))


@router.post("/support/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(
    body: CreateTicketRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TicketOut:
    return await support_service.create_ticket(
        session,
        user.id,
        subject=body.subject,
        body=body.body,
        category=body.category,
        priority=body.priority,
    )


@router.get("/support/tickets/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> TicketOut:
    ticket = await support_service.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket


@router.post("/support/tickets/{ticket_id}/messages", response_model=TicketOut)
async def reply_ticket(
    ticket_id: int,
    body: ReplyRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TicketOut:
    ticket = await support_service.add_merchant_message(session, ticket_id, user.id, body.body)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket introuvable")
    return ticket


@router.get("/releases", response_model=ListResponse[ReleaseNoteOut])
async def list_releases(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> ListResponse[ReleaseNoteOut]:
    items = await support_service.list_published_releases(session)
    return ListResponse(items=items, total=len(items))
