"""Carnet sanitaire HACCP : plan de nettoyage + traçabilité des exécutions.

Complète la chaîne du froid (relevés de température automatiques) : les tâches
d'hygiène récurrentes (nettoyage, désinfection…) sont définies par le commerce et
chaque exécution est **horodatée** (qui, quand, note) — preuve en cas de contrôle.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class HygieneTask(Base, TenantMixin, TimestampMixin):
    """Tâche d'hygiène récurrente du plan de nettoyage."""

    __tablename__ = "hygiene_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # daily | weekly | monthly — fréquence attendue de l'exécution.
    frequency: Mapped[str] = mapped_column(String(16), default="daily", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    records: Mapped[list[HygieneRecord]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class HygieneRecord(Base, TenantMixin, TimestampMixin):
    """Exécution horodatée d'une tâche d'hygiène (preuve de traçabilité)."""

    __tablename__ = "hygiene_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("hygiene_task.id", ondelete="CASCADE"), index=True
    )
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    done_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[HygieneTask] = relationship(back_populates="records")
