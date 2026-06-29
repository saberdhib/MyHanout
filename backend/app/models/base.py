"""Mixins et énumérations partagés par les modèles."""

from __future__ import annotations

import enum


class IntEnum(str, enum.Enum):
    """Base pour énumérations stockées en texte (lisibles en base)."""


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    PAID = "paid"
    OVERDUE = "overdue"
    ERROR = "error"


class OcrStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"  # human-in-the-loop
    APPROVED = "approved"
    SENT = "sent"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class EventType(str, enum.Enum):
    STOCK_LOW = "stock_low"
    STOCK_EXPIRING = "stock_expiring"
    INVOICE_DUE = "invoice_due"
    FORECAST_READY = "forecast_ready"
    AGENT_ACTION = "agent_action"
