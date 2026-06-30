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


# Familles produit (notion de regroupement ; les produits unitaires importent peu).
# Stockées en texte libre sur `product.family` ; cette liste sert de suggestions UI.
PRODUCT_FAMILIES: list[str] = [
    "viande",
    "fruits_legumes",
    "semoule_farine",
    "conserve",
    "boisson",
    "epice",
    "cremerie",
    "autre",
]


class PriceKind(enum.StrEnum):
    """Type de prix suivi dans l'historique."""

    PURCHASE = "purchase"  # coût d'achat
    SALE = "sale"  # prix de vente


class MeatSpecies(enum.StrEnum):
    BOEUF = "boeuf"
    VEAU = "veau"
    AGNEAU = "agneau"
    VOLAILLE = "volaille"
    PORC = "porc"
    AUTRE = "autre"


class MeatLotStatus(enum.StrEnum):
    RECEIVED = "received"  # bête reçue, pas encore travaillée
    BREAKING = "breaking"  # en cours de découpe/désossage
    DONE = "done"  # décomposition terminée (réel saisi)


class SignalKind(enum.StrEnum):
    """Nature d'un signal externe pouvant influencer la demande."""

    WEATHER = "weather"  # météo (température, pluie…)
    HOLIDAY = "holiday"  # vacances scolaires / jours fériés
    FUEL = "fuel"  # prix du carburant
    SPORTS = "sports"  # événements sportifs (matchs)
    ECONOMIC = "economic"  # indices éco (inflation, pouvoir d'achat)
    CUSTOM = "custom"  # source ajoutée par le commerçant


class RelationKind(enum.StrEnum):
    """Relation statistique entre deux produits."""

    SUBSTITUTE = "substitute"  # l'un remplace l'autre (rupture → report)
    COMPLEMENT = "complement"  # se vendent ensemble (halo)


class PipelineStatus(enum.StrEnum):
    """État d'un run de pipeline data (orchestration traçable)."""

    PENDING = "pending"  # créé, pas encore démarré
    RUNNING = "running"  # en cours
    SUCCESS = "success"  # terminé sans erreur
    FAILED = "failed"  # terminé en erreur (champ error renseigné)


class PipelineTrigger(enum.StrEnum):
    """Origine du déclenchement d'un run (traçabilité)."""

    SCHEDULE = "schedule"  # planifié (Celery beat)
    MANUAL = "manual"  # déclenché par un opérateur (Data Ops)
    MERCHANT = "merchant"  # déclenché par le commerçant (human-in-the-loop)


class RecommendationStatus(enum.StrEnum):
    """Cycle de vie d'une recommandation (aide à la décision, pas action auto)."""

    SUGGESTED = "suggested"  # proposée par le moteur (à valider)
    ACCEPTED = "accepted"  # retenue par le commerçant
    DISMISSED = "dismissed"  # écartée par le commerçant


class MarkdownStatus(enum.StrEnum):
    """Cycle de vie d'une suggestion de démarque (anti-gaspillage, human-in-the-loop)."""

    SUGGESTED = "suggested"  # proposée par l'agent Démarque (à valider)
    APPLIED = "applied"  # démarque appliquée par le commerçant
    REJECTED = "rejected"  # écartée par le commerçant


class AlertStatus(enum.StrEnum):
    """État d'une alerte (human-in-the-loop : résolution manuelle)."""

    OPEN = "open"  # active, non traitée
    ACKNOWLEDGED = "acknowledged"  # vue, en cours de traitement
    RESOLVED = "resolved"  # résolue par un humain (auditée)
    DISMISSED = "dismissed"  # écartée (faux positif)


class AlertPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertKind(enum.StrEnum):
    """Type d'alerte (règle déclencheuse, lisible/auditable)."""

    STOCK_OUT = "stock_out"  # risque de rupture
    OVERSTOCK = "overstock"  # surstock / risque de démarque
    EXPIRY = "expiry"  # péremption proche (périssable)
    FORECAST_DRIFT = "forecast_drift"  # dérive de la précision (MAPE)
    DATA_STALE = "data_stale"  # données plus fraîches (pipeline en retard)
    CASH = "cash"  # tension de trésorerie
