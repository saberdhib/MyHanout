"""Service réservations client (click & collect).

Cycle human-in-the-loop : pending → confirmed → ready (notification client) →
collected (crédit fidélité si client connu) | cancelled. Notification transactionnelle
via le résolveur WhatsApp (le client est informé de SA commande). Rechargement explicite
des lignes (évite le lazy-load async).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.product import Product
from app.models.reservation import Reservation, ReservationLine, ReservationStatus
from app.schemas.reservation import (
    ReservationLineIn,
    ReservationLineOut,
    ReservationOut,
)

_STATUS_LABEL = {
    ReservationStatus.PENDING: "à valider",
    ReservationStatus.CONFIRMED: "validée",
    ReservationStatus.READY: "prête à récupérer",
    ReservationStatus.COLLECTED: "récupérée",
    ReservationStatus.CANCELLED: "annulée",
}


async def _lines_out(session: AsyncSession, reservation_id: int) -> list[ReservationLineOut]:
    rows = await session.scalars(
        select(ReservationLine)
        .where(ReservationLine.reservation_id == reservation_id)
        .order_by(ReservationLine.id)
    )
    return [
        ReservationLineOut(
            id=ln.id,
            product_id=ln.product_id,
            product_name=ln.product_name,
            quantity=float(ln.quantity),
            unit_price=float(ln.unit_price),
            line_total=float(ln.line_total),
        )
        for ln in rows
    ]


def _explain(r: Reservation) -> str:
    label = _STATUS_LABEL.get(ReservationStatus(r.status), str(r.status))
    who = r.customer_name or (f"client #{r.customer_id}" if r.customer_id else "client de passage")
    return f"Réservation {label} · {who} · {float(r.total_amount):.2f} €."


async def _out(session: AsyncSession, r: Reservation) -> ReservationOut:
    return ReservationOut(
        id=r.id,
        customer_id=r.customer_id,
        customer_name=r.customer_name,
        customer_phone=r.customer_phone,
        status=str(r.status),
        pickup_date=r.pickup_date.isoformat() if r.pickup_date else None,
        notes=r.notes,
        total_amount=float(r.total_amount),
        loyalty_credited=r.loyalty_credited,
        created_at=r.created_at.isoformat() if r.created_at else None,
        lines=await _lines_out(session, r.id),
        explanation=_explain(r),
    )


async def create_reservation(
    session: AsyncSession,
    *,
    customer_id: int | None,
    customer_name: str | None,
    customer_phone: str | None,
    pickup_date: str | None,
    notes: str | None,
    lines: list[ReservationLineIn],
) -> ReservationOut:
    products = {
        p.id: p
        for p in await session.scalars(
            select(Product).where(Product.id.in_([ln.product_id for ln in lines]))
        )
    }
    reservation = Reservation(
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        pickup_date=date.fromisoformat(pickup_date) if pickup_date else None,
        notes=notes,
        status=ReservationStatus.PENDING,
    )
    session.add(reservation)
    await session.flush()

    total = 0.0
    for ln in lines:
        prod = products.get(ln.product_id)
        if prod is None:
            raise AppError(f"Produit #{ln.product_id} introuvable")
        price = ln.unit_price if ln.unit_price is not None else float(prod.unit_price or 0)
        line_total = round(price * ln.quantity, 2)
        total += line_total
        session.add(
            ReservationLine(
                reservation_id=reservation.id,
                product_id=prod.id,
                product_name=prod.name,
                quantity=ln.quantity,
                unit_price=price,
                line_total=line_total,
            )
        )
    reservation.total_amount = round(total, 2)
    await session.commit()
    return await _out(session, reservation)


async def list_reservations(
    session: AsyncSession, status: str | None = None
) -> list[ReservationOut]:
    stmt = select(Reservation).order_by(Reservation.id.desc())
    if status:
        stmt = stmt.where(Reservation.status == ReservationStatus(status))
    rows = list(await session.scalars(stmt))
    return [await _out(session, r) for r in rows]


async def get_reservation(session: AsyncSession, reservation_id: int) -> ReservationOut | None:
    r = await session.get(Reservation, reservation_id)
    return await _out(session, r) if r is not None else None


async def set_status(
    session: AsyncSession, reservation_id: int, status: str, user_id: int
) -> ReservationOut | None:
    if status not in {s.value for s in ReservationStatus}:
        raise AppError(f"Statut invalide : {status}")
    r = await session.get(Reservation, reservation_id)
    if r is None:
        return None
    if r.status in (ReservationStatus.COLLECTED, ReservationStatus.CANCELLED):
        raise AppError("Réservation déjà clôturée (récupérée ou annulée).")

    new = ReservationStatus(status)
    r.status = new

    # Prête → on informe le client (message transactionnel sur SA commande).
    if new == ReservationStatus.READY and r.customer_phone:
        from app.messaging.resolver import resolve_whatsapp_client

        client = await resolve_whatsapp_client(session)
        await client.send_text(
            r.customer_phone,
            f"Votre commande est prête à récupérer ({float(r.total_amount):.2f} €). À bientôt !",
        )

    # Récupérée → crédit fidélité (one-shot, client connu uniquement).
    if new == ReservationStatus.COLLECTED and r.customer_id and not r.loyalty_credited:
        from app.services.loyalty_service import earn

        await earn(
            session,
            r.customer_id,
            float(r.total_amount),
            reason=f"Retrait commande #{r.id}",
        )
        r.loyalty_credited = True

    await session.commit()
    return await _out(session, r)
