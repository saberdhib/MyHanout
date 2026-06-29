"""Mixins et énumérations partagés par les modèles.

Les énumérations héritent de `enum.StrEnum` : la valeur (minuscule) est utilisée
en base via `values_callable` sur les colonnes Enum, en cohérence avec les
valeurs par défaut de la migration et des seeds.
"""

from __future__ import annotations

import enum


class InvoiceStatus(enum.StrEnum):
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"  # OCR fait, en attente de validation humaine
    APPROVED = "approved"  # validée par un humain -> lignes écrites
    REJECTED = "rejected"  # rejetée par un humain (motif requis)
    PROCESSED = "processed"
    PAID = "paid"
    OVERDUE = "overdue"
    ERROR = "error"


class OcrStatus(enum.StrEnum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class OrderStatus(enum.StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"  # human-in-the-loop
    APPROVED = "approved"
    SENT = "sent"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class EventType(enum.StrEnum):
    STOCK_LOW = "stock_low"
    STOCK_EXPIRING = "stock_expiring"
    INVOICE_DUE = "invoice_due"
    FORECAST_READY = "forecast_ready"
    AGENT_ACTION = "agent_action"
