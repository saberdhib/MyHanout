"""Schémas facture."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None = None
    description: str | None = None
    quantity: float
    unit_price: float
    line_total: float


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str | None = None
    supplier_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    total_amount: float | None = None
    currency: str
    status: str
    ocr_status: str
    lines: list[InvoiceLineOut] = []
