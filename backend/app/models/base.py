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
    SUGGESTED = "suggested"  # proposée par le système, non validée
    PENDING_APPROVAL = "pending_approval"  # human-in-the-loop
    CONFIRMED = "confirmed"  # validée par un humain (suggestion ajustée)
    APPROVED = "approved"
    SENT = "sent"  # message fournisseur envoyé (mode whatsapp_auto)
    RECEIVED = "received"
    CANCELLED = "cancelled"


class OrderActionMode(enum.StrEnum):
    """Comment la commande validée est transmise au fournisseur."""

    WHATSAPP_AUTO = "whatsapp_auto"  # message WhatsApp auto au fournisseur
    DRAFT = "draft"  # brouillon à copier/coller par le commerçant
    RECORD_ONLY = "record_only"  # enregistrement seul (il appelle lui-même)


class DailyEntrySource(enum.StrEnum):
    WHATSAPP = "whatsapp"
    DASHBOARD = "dashboard"
    MANUAL = "manual"


class CampaignStatus(enum.StrEnum):
    DRAFT = "draft"  # proposée par l'IA, non publiée (human-in-the-loop)
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class EventType(enum.StrEnum):
    STOCK_LOW = "stock_low"
    STOCK_EXPIRING = "stock_expiring"
    INVOICE_DUE = "invoice_due"
    FORECAST_READY = "forecast_ready"
    AGENT_ACTION = "agent_action"


class ExpenseKind(enum.StrEnum):
    """Nature comptable d'une charge (pré-compta, non certifiée)."""

    OPEX = "opex"  # charge d'exploitation (récurrente)
    CAPEX = "capex"  # investissement (immobilisable)
    UNKNOWN = "unknown"  # non encore classé


class ClassificationSource(enum.StrEnum):
    """Origine d'une classification de facture."""

    AI = "ai"  # proposée par le classifieur (à valider)
    HUMAN = "human"  # validée/corrigée par un humain
    RULE = "rule"  # posée par une règle déterministe


class EquipmentKind(enum.StrEnum):
    """Type d'équipement suivi (chaîne du froid + autres machines)."""

    FRIDGE = "fridge"  # réfrigérateur (positif)
    FREEZER = "freezer"  # congélateur (négatif)
    OVEN = "oven"  # four / chaud
    OTHER = "other"
