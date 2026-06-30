"""Schémas Pydantic de la démarque (anti-gaspillage frais)."""

from __future__ import annotations

from pydantic import BaseModel


class MarkdownDecision(BaseModel):
    """Décision produite par le moteur de démarque (pure, testable, explicable)."""

    product_id: int
    quantity_at_risk: float
    days_to_expiry: int
    current_price: float
    suggested_price: float
    discount_pct: int
    expected_units_cleared: float
    recovered_value: float
    avoided_loss: float
    baseline_loss: float
    confidence: float
    score: float
    explanation: str
    reasons: list[str] = []
    data_used: dict = {}


class MarkdownOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity_at_risk: float
    expiry_date: str | None = None
    days_to_expiry: int
    current_price: float
    suggested_price: float
    discount_pct: int
    expected_units_cleared: float
    recovered_value: float
    avoided_loss: float
    baseline_loss: float
    confidence: float
    score: float
    status: str
    model_version: str
    pipeline_run_id: int | None = None
    explanation: str
