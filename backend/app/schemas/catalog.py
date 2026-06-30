"""Schémas catalogue : gestion produits + familles."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    category: str | None = None
    family: str | None = None
    unit: str
    unit_price: float | None = None
    perishable: bool = False
    shelf_life_days: int | None = None
    supplier_id: int | None = None


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    family: str | None = None
    unit: str = "unit"
    unit_price: float | None = None
    perishable: bool = False
    shelf_life_days: int | None = None
    supplier_id: int | None = None


class ProductUpdate(BaseModel):
    """Champs éditables (tous optionnels — mise à jour partielle)."""

    name: str | None = None
    category: str | None = None
    family: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    perishable: bool | None = None
    shelf_life_days: int | None = None
    supplier_id: int | None = None
