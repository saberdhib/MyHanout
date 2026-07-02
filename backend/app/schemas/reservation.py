"""Schémas réservations client (click & collect)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReservationLineIn(BaseModel):
    product_id: int
    quantity: float = Field(gt=0, default=1)
    unit_price: float | None = None  # défaut : prix catalogue du produit


class ReservationLineOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: float
    unit_price: float
    line_total: float


class CreateReservationRequest(BaseModel):
    customer_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    pickup_date: str | None = None  # ISO date
    notes: str | None = None
    lines: list[ReservationLineIn] = Field(min_length=1)


class SetReservationStatusRequest(BaseModel):
    status: str  # pending | confirmed | ready | collected | cancelled


class ReservationOut(BaseModel):
    id: int
    customer_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    status: str
    pickup_date: str | None = None
    notes: str | None = None
    total_amount: float
    loyalty_credited: bool
    created_at: str | None = None
    lines: list[ReservationLineOut] = []
    explanation: str | None = None
