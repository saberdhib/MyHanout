"""Briefing du matin : consolidation des agents en tâches du jour priorisées.

L'agent « Tâches du jour » agrège alertes + réassort + démarques + production en
une liste d'actions priorisées, explicable, que le commerçant valide une par une
(human-in-the-loop). Peut être poussé sur WhatsApp/Slack.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import BriefingStatus
from app.models.tenant import TenantMixin


class DailyBriefing(Base, TenantMixin, TimestampMixin):
    __tablename__ = "daily_briefing"

    id: Mapped[int] = mapped_column(primary_key=True)
    briefing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run.id"), nullable=True, index=True
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)  # impact € estimé
    status: Mapped[BriefingStatus] = mapped_column(
        Enum(
            BriefingStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=BriefingStatus.DRAFT,
        index=True,
    )

    items: Mapped[list[BriefingItem]] = relationship(
        back_populates="briefing", cascade="all, delete-orphan"
    )


class BriefingItem(Base, TenantMixin, TimestampMixin):
    __tablename__ = "briefing_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    briefing_id: Mapped[int] = mapped_column(ForeignKey("daily_briefing.id"), index=True)
    # alert | reassort | markdown | production
    category: Mapped[str] = mapped_column(String(32), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 = haute, 3 = basse
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # explication
    action: Mapped[str | None] = mapped_column(String(255), nullable=True)  # action suggérée
    value: Mapped[float] = mapped_column(Float, default=0.0)  # impact € estimé
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)

    briefing: Mapped[DailyBriefing] = relationship(back_populates="items")
