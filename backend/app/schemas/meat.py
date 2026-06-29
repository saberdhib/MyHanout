"""Schémas boucherie (lots, coupes, rendement, traçabilité)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MeatCutIn(BaseModel):
    cut_label: str
    product_id: int | None = None
    expected_weight_kg: float | None = None
    actual_weight_kg: float | None = None
    is_waste: bool = False


class MeatLotIn(BaseModel):
    lot_code: str
    species: str = "boeuf"
    label: str
    supplier_id: int | None = None
    gross_weight_kg: float
    purchase_cost: float
    received_at: datetime | None = None
    notes: str | None = None


class MeatCutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cut_label: str
    product_id: int | None = None
    expected_weight_kg: float | None = None
    actual_weight_kg: float | None = None
    is_waste: bool
    allocated_cost: float | None = None
    cost_per_kg: float | None = None
    explanation: str | None = None


class MeatLotSummary(BaseModel):
    id: int
    lot_code: str
    species: str
    label: str
    status: str
    supplier_id: int | None = None
    gross_weight_kg: float
    purchase_cost: float
    saleable_weight_kg: float
    waste_weight_kg: float
    yield_pct: float | None  # rendement = valorisable / brut
    cost_per_kg: float | None
    cuts: list[MeatCutOut] = []
    traceability: str  # lot → fournisseur → date (chaîne de traçabilité)
    explanation: str
