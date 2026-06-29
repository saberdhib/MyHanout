"""Campagnes promo flash (ex. produit en fin de vie) — human-in-the-loop."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import CampaignStatus
from app.models.tenant import TenantMixin


class PromoCampaign(Base, TenantMixin, TimestampMixin):
    __tablename__ = "promo_campaign"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)  # contenu généré (éditable avant envoi)
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    # Explicabilité : pourquoi cette promo est proposée (fin de vie, météo, tendance).
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=CampaignStatus.DRAFT,
    )
    # Canaux ciblés (CSV : social, customers).
    channels: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audience_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Visuel généré (affiche promo) : data URL + prompt pour la traçabilité.
    visual_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
