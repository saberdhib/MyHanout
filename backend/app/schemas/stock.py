"""Schémas stock."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: float
    location: str | None = None
    reorder_threshold: float
    expiry_date: date | None = None


class StockWithProduct(StockOut):
    """Stock enrichi du nom de produit pour le dashboard."""

    product_name: str | None = None
    product_sku: str | None = None
    low_stock: bool = False
