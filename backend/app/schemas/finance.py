"""Schémas de la couche financière (pré-compta / pilotage, non certifié)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

# Mention récurrente : on fait du pilotage, pas de la comptabilité certifiée.
DISCLAIMER = "Estimation de pilotage (pré-compta) — non comptabilité certifiée."


# --- Trésorerie -------------------------------------------------------------
class TreasuryLine(BaseModel):
    label: str
    amount: float
    explanation: str


class TreasuryView(BaseModel):
    period_from: date
    period_to: date
    currency: str = "EUR"
    sales_in: float
    outflows_paid: float
    estimated_balance: float
    upcoming_7d: float
    upcoming_30d: float
    alert: str | None = None
    lines: list[TreasuryLine] = []
    disclaimer: str = DISCLAIMER


# --- Valorisation du stock --------------------------------------------------
class InventoryItem(BaseModel):
    product_id: int
    product_name: str | None
    quantity: float
    unit_cost: float
    value: float
    at_risk: bool
    explanation: str


class InventoryValuation(BaseModel):
    currency: str = "EUR"
    total_value: float
    at_risk_value: float
    items: list[InventoryItem] = []
    explanation: str
    disclaimer: str = DISCLAIMER


# --- Marges -----------------------------------------------------------------
class ProductMargin(BaseModel):
    product_id: int
    product_name: str | None
    units_sold: float
    avg_sale_price: float
    last_cost: float
    margin_unit: float
    margin_pct: float | None
    cost_trend: str | None = None  # "up" | "down" | "stable"
    signal: str | None = None  # alerte explicable si dégradation
    explanation: str


class MarginReport(BaseModel):
    period_from: date
    period_to: date
    items: list[ProductMargin] = []
    explanation: str
    disclaimer: str = DISCLAIMER


# --- Catégories & classification -------------------------------------------
class ExpenseCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    kind: str
    accounting_hint: str | None = None


class InvoiceClassificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str | None = None
    supplier_id: int | None = None
    total_amount: float | None = None
    currency: str
    paid: bool
    category_id: int | None = None
    expense_kind: str
    classification_source: str | None = None
    classification_confidence: float | None = None
    classification_explanation: str | None = None


class ClassifyConfirmRequest(BaseModel):
    category_id: int | None = None
    kind: str | None = None  # opex | capex
    note: str | None = None


# --- Alertes finance --------------------------------------------------------
class FinanceAlert(BaseModel):
    type: str  # duplicate_invoice | price_anomaly | margin_drop | due_soon
    severity: str  # info | warning | critical
    title: str
    reason: str
    invoice_ids: list[int] = []
    product_id: int | None = None


class FinanceAlerts(BaseModel):
    alerts: list[FinanceAlert] = []
    explanation: str


# --- Échéancier fournisseurs + trésorerie prévisionnelle --------------------
class PayableInvoice(BaseModel):
    invoice_id: int
    number: str | None = None
    supplier_name: str | None = None
    due_date: str | None = None
    amount: float
    days_to_due: int | None = None  # négatif = en retard
    overdue: bool


class PayableBucket(BaseModel):
    key: str  # overdue | d7 | d30 | later | no_date
    label: str
    count: int
    amount: float
    invoices: list[PayableInvoice] = []


class CashWeek(BaseModel):
    week_start: str
    expected_inflow: float
    payables_due: float
    net: float
    running_balance: float
    explanation: str


class PayablesView(BaseModel):
    currency: str = "EUR"
    total_due: float
    overdue_amount: float
    opening_balance: float
    buckets: list[PayableBucket] = []
    weeks: list[CashWeek] = []
    alert: str | None = None
    explanation: str
    disclaimer: str
