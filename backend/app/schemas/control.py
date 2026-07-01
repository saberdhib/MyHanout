"""Schémas Pydantic des contrôles : 3-way match factures + démarque inconnue."""

from __future__ import annotations

from pydantic import BaseModel


# --- Contrôle factures (3-way match) ---
class InvoiceFinding(BaseModel):
    invoice_id: int
    invoice_number: str
    supplier_name: str | None = None
    product_id: int
    product_name: str | None = None
    kind: str  # price_drift | price_vs_order | qty_vs_order
    expected: float
    observed: float
    overcharge: float  # € payés en trop (estimation)
    explanation: str


class InvoiceControlReport(BaseModel):
    findings: list[InvoiceFinding] = []
    total_overcharge: float = 0.0
    invoices_checked: int = 0
    explanation: str


# --- Démarque inconnue (vol / casse / erreurs) ---
class ShrinkageItem(BaseModel):
    product_id: int
    product_name: str | None = None
    baseline_date: str
    baseline_qty: float
    purchased_since: float
    sold_since: float
    expected_stock: float
    actual_stock: float
    missing_units: float
    estimated_loss: float  # valorisé au coût d'achat
    explanation: str


class ShrinkageReport(BaseModel):
    items: list[ShrinkageItem] = []
    total_loss: float = 0.0
    products_checked: int = 0
    explanation: str
