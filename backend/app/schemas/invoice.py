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
    ocr_confidence: float | None = None
    review_reason: str | None = None
    paid: bool = False
    lines: list[InvoiceLineOut] = []


class InvoiceReviewOut(InvoiceOut):
    """Réponse d'upload/review : facture + raisons explicables de la revue."""

    reasons: list[str] = []


class InvoiceRejectRequest(BaseModel):
    reason: str


class InvoiceUpdate(BaseModel):
    """Édition manuelle d'une facture (champs pré-remplis côté UI, tous optionnels)."""

    number: str | None = None
    supplier_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    total_amount: float | None = None
    paid: bool | None = None
