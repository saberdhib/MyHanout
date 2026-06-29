"""Schémas commandes : suggestion explicable + validation + action."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.models.base import OrderActionMode


class SuggestionLine(BaseModel):
    """Une ligne de suggestion, avec son explication (obligatoire)."""

    product_id: int
    product_name: str | None = None
    unit: str = "unit"
    suggested_quantity: float
    predicted_demand: float
    safety_buffer: float
    current_stock: float
    lead_time_days: int
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str


class SuggestRequest(BaseModel):
    # Horizon en jours OU mot-clé ("demain", "semaine"/"semaine prochaine").
    horizon_days: int | None = None
    horizon: str | None = None
    product_ids: list[int] | None = None


class SuggestionOut(BaseModel):
    horizon_days: int
    generated_for: date
    model: str
    lines: list[SuggestionLine] = []


class AdjustedLine(BaseModel):
    product_id: int
    quantity: float


class ConfirmOrderRequest(BaseModel):
    """Validation humaine d'une suggestion ajustée -> commande `confirmed`."""

    supplier_id: int | None = None
    lines: list[AdjustedLine]
    action_mode: OrderActionMode | None = None  # surcharge le mode du fournisseur


class OrderLineOut(BaseModel):
    product_id: int
    quantity: float
    unit_price: float


class OrderOut(BaseModel):
    id: int
    supplier_id: int | None = None
    status: str
    action_mode: str
    total_amount: float
    supplier_message: str | None = None
    lines: list[OrderLineOut] = []
