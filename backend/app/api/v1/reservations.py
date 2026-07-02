"""Endpoints réservations client (click & collect) — human-in-the-loop."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.reservation import (
    CreateReservationRequest,
    ReservationOut,
    SetReservationStatusRequest,
)
from app.services import reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=ListResponse[ReservationOut])
async def list_reservations(
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ListResponse[ReservationOut]:
    items = await reservation_service.list_reservations(session, status)
    return ListResponse(items=items, total=len(items))


@router.get("/{reservation_id}", response_model=ReservationOut)
async def get_reservation(
    reservation_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ReservationOut:
    r = await reservation_service.get_reservation(session, reservation_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    return r


@router.post("", response_model=ReservationOut, status_code=201)
async def create_reservation(
    body: CreateReservationRequest,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("orders")),
) -> ReservationOut:
    return await reservation_service.create_reservation(
        session,
        customer_id=body.customer_id,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        pickup_date=body.pickup_date,
        notes=body.notes,
        lines=body.lines,
    )


@router.post("/{reservation_id}/status", response_model=ReservationOut)
async def set_status(
    reservation_id: int,
    body: SetReservationStatusRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("orders")),
) -> ReservationOut:
    """Fait avancer la réservation (validation, prête→notif, récupérée→fidélité)."""
    r = await reservation_service.set_status(session, reservation_id, body.status, user.id)
    if r is None:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    return r
