"""Suggestion de démarque (anti-gaspillage frais), explicable et traçable.

Produite par l'**agent Démarque** : pour un lot périssable dont la péremption
approche, propose une remise (palier %) calculée pour écouler l'invendu prévu en
récupérant un maximum de marge plutôt que de subir une perte totale.

Human-in-the-loop : statut `suggested` → action humaine → `applied`/`rejected`.
Chaque suggestion porte son **explication** + les **données utilisées** (audit).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import MarkdownStatus
from app.models.tenant import TenantMixin


class MarkdownSuggestion(Base, TenantMixin, TimestampMixin):
    __tablename__ = "markdown_suggestion"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    stock_id: Mapped[int | None] = mapped_column(ForeignKey("stock.id"), nullable=True, index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run.id"), nullable=True, index=True
    )
    model_version: Mapped[str] = mapped_column(String(64), default="v1")

    # Contexte du lot à risque.
    quantity_at_risk: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    days_to_expiry: Mapped[int] = mapped_column(Integer, default=0)

    # Proposition de prix.
    current_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    suggested_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_pct: Mapped[int] = mapped_column(Integer, default=0)

    # Impact économique estimé (explicabilité chiffrée).
    expected_units_cleared: Mapped[float] = mapped_column(Float, default=0.0)
    recovered_value: Mapped[float] = mapped_column(Float, default=0.0)  # cash récupéré
    avoided_loss: Mapped[float] = mapped_column(Float, default=0.0)  # perte évitée (coût)
    baseline_loss: Mapped[float] = mapped_column(Float, default=0.0)  # perte si on ne fait rien

    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1
    score: Mapped[float] = mapped_column(Float, default=0.0)  # priorité (tri)

    status: Mapped[MarkdownStatus] = mapped_column(
        Enum(
            MarkdownStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=MarkdownStatus.SUGGESTED,
        index=True,
    )
    explanation: Mapped[str] = mapped_column(Text)  # raison humaine (explicabilité)
    data_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON des entrées
