"""Schémas produit."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str | None = None
    unit: str
    unit_price: float | None = None
    perishable: bool
    shelf_life_days: int | None = None
    supplier_id: int | None = None
