"""Schémas Pydantic de l'agent Prix (prix conseillé, explicable)."""

from __future__ import annotations

from pydantic import BaseModel


class PriceDecision(BaseModel):
    """Décision produite par le moteur de prix (pure, testable, explicable)."""

    product_id: int
    current_price: float
    unit_cost: float
    current_margin: float  # marge actuelle (0..1)
    suggested_price: float
    target_margin: float  # marge au prix conseillé (0..1)
    action: str  # raise | lower | hold
    delta: float  # suggested - current
    confidence: float
    explanation: str
    reasons: list[str] = []


class PriceSuggestionOut(PriceDecision):
    product_name: str | None = None


class PriceApplyRequest(BaseModel):
    product_id: int
    price: float
