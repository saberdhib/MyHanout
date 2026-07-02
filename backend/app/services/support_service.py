"""Service Support & mises à jour (Lot 3).

Deux points de vue sur les mêmes tickets (TenantMixin) :
- **commerçant** : garde-fou actif → ne voit/agit que sur SES tickets.
- **plateforme** : `current_org=None` → voit/agit sur TOUS les tickets (audité).

⚠️ Écritures cross-tenant : quand la plateforme insère un message, on estampille
`organization_id` **explicitement** (le `before_flush` ne stampe qu'avec un org courant).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import tenant_context
from app.models.organization import Organization
from app.models.support import (
    ReleaseCategory,
    ReleaseNote,
    SupportMessage,
    SupportTicket,
    TicketPriority,
    TicketStatus,
)
from app.schemas.support import ReleaseNoteOut, TicketMessageOut, TicketOut


def _iso(v) -> str | None:
    return v.isoformat() if v else None


def _msg_out(m: SupportMessage) -> TicketMessageOut:
    return TicketMessageOut(
        id=m.id,
        author_kind=m.author_kind,
        author_user_id=m.author_user_id,
        body=m.body,
        created_at=_iso(m.created_at),
    )


def _ticket_out(
    t: SupportTicket,
    *,
    messages: list[SupportMessage] | None = None,
    org_name: str | None = None,
) -> TicketOut:
    # `messages` fourni explicitement (chargé via requête) pour éviter tout lazy-load
    # async (MissingGreenlet) ; sinon on lit la relation déjà chargée.
    msgs = messages if messages is not None else list(t.messages)
    return TicketOut(
        id=t.id,
        subject=t.subject,
        category=t.category,
        status=str(t.status),
        priority=str(t.priority),
        created_by_user_id=t.created_by_user_id,
        assigned_admin_id=t.assigned_admin_id,
        created_at=_iso(t.created_at),
        updated_at=_iso(t.updated_at),
        messages=[_msg_out(m) for m in msgs],
        organization_id=t.organization_id,
        organization_name=org_name,
    )


async def _load_messages(session: AsyncSession, ticket_id: int) -> list[SupportMessage]:
    return list(
        await session.scalars(
            select(SupportMessage)
            .where(SupportMessage.ticket_id == ticket_id)
            .order_by(SupportMessage.id)
        )
    )


# --- Côté commerçant (garde-fou actif) --------------------------------------


async def _merchant_ticket_dto(session: AsyncSession, ticket_id: int) -> TicketOut | None:
    """Construit le DTO d'un ticket (garde-fou actif → forcément celui du commerçant).

    Rechargement explicite (colonnes + messages) pour éviter tout lazy-load async.
    """
    ticket = await session.get(SupportTicket, ticket_id)
    if ticket is None:
        return None
    await session.refresh(ticket)
    msgs = await _load_messages(session, ticket_id)
    return _ticket_out(ticket, messages=msgs)


async def create_ticket(
    session: AsyncSession,
    user_id: int,
    *,
    subject: str,
    body: str,
    category: str | None,
    priority: str,
) -> TicketOut:
    prio = (
        TicketPriority(priority)
        if priority in {p.value for p in TicketPriority}
        else (TicketPriority.NORMAL)
    )
    ticket = SupportTicket(
        subject=subject,
        category=category,
        priority=prio,
        status=TicketStatus.OPEN,
        created_by_user_id=user_id,
    )
    session.add(ticket)
    await session.flush()
    # Premier message = le corps de la demande.
    session.add(
        SupportMessage(
            ticket_id=ticket.id, author_user_id=user_id, author_kind="merchant", body=body
        )
    )
    await session.commit()
    dto = await _merchant_ticket_dto(session, ticket.id)
    assert dto is not None
    return dto


async def list_tickets(session: AsyncSession, status: str | None = None) -> list[SupportTicket]:
    stmt = select(SupportTicket).order_by(SupportTicket.id.desc())
    if status:
        stmt = stmt.where(SupportTicket.status == TicketStatus(status))
    return list(await session.scalars(stmt))


async def get_ticket(session: AsyncSession, ticket_id: int) -> TicketOut | None:
    return await _merchant_ticket_dto(session, ticket_id)


async def add_merchant_message(
    session: AsyncSession, ticket_id: int, user_id: int, body: str
) -> TicketOut | None:
    ticket = await session.get(SupportTicket, ticket_id)
    if ticket is None:
        return None
    session.add(
        SupportMessage(
            ticket_id=ticket.id, author_user_id=user_id, author_kind="merchant", body=body
        )
    )
    # Une réponse du commerçant rouvre la demande (elle attend le support).
    if ticket.status in (TicketStatus.PENDING, TicketStatus.RESOLVED):
        ticket.status = TicketStatus.OPEN
    await session.commit()
    return await _merchant_ticket_dto(session, ticket_id)


# --- Côté plateforme (cross-tenant, audité) ---------------------------------


async def list_all_tickets(session: AsyncSession, status: str | None = None) -> list[TicketOut]:
    with tenant_context(None):
        stmt = select(SupportTicket).order_by(SupportTicket.id.desc())
        if status:
            stmt = stmt.where(SupportTicket.status == TicketStatus(status))
        tickets = list(await session.scalars(stmt))
        names = {o.id: o.name for o in await session.scalars(select(Organization))}
        msgs_by_ticket = {}
        for t in tickets:
            await session.refresh(t)  # colonnes chargées via IO awaité
            msgs_by_ticket[t.id] = await _load_messages(session, t.id)
    return [
        _ticket_out(t, messages=msgs_by_ticket[t.id], org_name=names.get(t.organization_id))
        for t in tickets
    ]


async def get_ticket_platform(session: AsyncSession, ticket_id: int) -> TicketOut | None:
    with tenant_context(None):
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            return None
        await session.refresh(ticket)  # colonnes chargées via IO awaité (post-commit)
        msgs = await _load_messages(session, ticket_id)
        org = await session.get(Organization, ticket.organization_id)
        name = org.name if org else None
    return _ticket_out(ticket, messages=msgs, org_name=name)


async def platform_reply(
    session: AsyncSession, ticket_id: int, admin_user_id: int, body: str
) -> TicketOut | None:
    from app.services.platform_service import platform_audit

    with tenant_context(None):
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            return None
        # Écriture cross-tenant : on estampille l'org explicitement.
        session.add(
            SupportMessage(
                organization_id=ticket.organization_id,
                ticket_id=ticket.id,
                author_user_id=admin_user_id,
                author_kind="platform",
                body=body,
            )
        )
        if ticket.assigned_admin_id is None:
            ticket.assigned_admin_id = admin_user_id
        # Réponse du support → en attente du commerçant.
        ticket.status = TicketStatus.PENDING
        await platform_audit(
            session,
            admin_user_id,
            "ticket_reply",
            org_id=ticket.organization_id,
            detail={"ticket_id": ticket_id},
        )
        await session.commit()
    return await get_ticket_platform(session, ticket_id)


async def set_ticket_status(
    session: AsyncSession, ticket_id: int, admin_user_id: int, status: str
) -> TicketOut | None:
    from app.services.platform_service import platform_audit

    if status not in {s.value for s in TicketStatus}:
        raise ValueError(f"Statut de ticket invalide : {status}")
    with tenant_context(None):
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            return None
        ticket.status = TicketStatus(status)
        await platform_audit(
            session,
            admin_user_id,
            "ticket_status",
            org_id=ticket.organization_id,
            detail={"ticket_id": ticket_id, "status": status},
        )
        await session.commit()
    return await get_ticket_platform(session, ticket_id)


# --- Notes de version (changelog produit) -----------------------------------


def _release_out(r: ReleaseNote) -> ReleaseNoteOut:
    return ReleaseNoteOut(
        id=r.id,
        version=r.version,
        title=r.title,
        body=r.body,
        category=str(r.category),
        published=r.published,
        published_at=_iso(r.published_at),
        created_at=_iso(r.created_at),
    )


async def list_published_releases(session: AsyncSession) -> list[ReleaseNoteOut]:
    # ReleaseNote est GLOBALE (non tenant) : lisible par tous les commerces.
    rows = await session.scalars(
        select(ReleaseNote).where(ReleaseNote.published.is_(True)).order_by(ReleaseNote.id.desc())
    )
    return [_release_out(r) for r in rows]


async def list_all_releases(session: AsyncSession) -> list[ReleaseNoteOut]:
    with tenant_context(None):
        rows = await session.scalars(select(ReleaseNote).order_by(ReleaseNote.id.desc()))
        return [_release_out(r) for r in rows]


async def create_release(
    session: AsyncSession,
    admin_user_id: int,
    *,
    version: str,
    title: str,
    body: str,
    category: str,
) -> ReleaseNoteOut:
    from app.services.platform_service import platform_audit

    cat = (
        ReleaseCategory(category)
        if category in {c.value for c in ReleaseCategory}
        else ReleaseCategory.FEATURE
    )
    with tenant_context(None):
        note = ReleaseNote(
            version=version,
            title=title,
            body=body,
            category=cat,
            created_by_admin_id=admin_user_id,
        )
        session.add(note)
        await platform_audit(session, admin_user_id, "release_create", detail={"version": version})
        await session.commit()
        await session.refresh(note)
        return _release_out(note)


async def publish_release(
    session: AsyncSession, note_id: int, admin_user_id: int
) -> ReleaseNoteOut | None:
    from app.services.platform_service import platform_audit

    with tenant_context(None):
        note = await session.get(ReleaseNote, note_id)
        if note is None:
            return None
        note.published = True
        note.published_at = datetime.now(UTC)
        await platform_audit(
            session, admin_user_id, "release_publish", detail={"version": note.version}
        )
        await session.commit()
        await session.refresh(note)
        return _release_out(note)
