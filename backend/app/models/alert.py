"""Alerte décisionnelle (règle lisible → priorité → résolution humaine).

Distincte de `event` (notifications techniques génériques, non tenant) : l'alerte
est une **entité métier tenant**, première-classe du dashboard décisionnel, avec
règle déclencheuse, seuil, priorité, action recommandée et **résolution manuelle
auditée** (human-in-the-loop).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import AlertKind, AlertPriority, AlertStatus
from app.models.tenant import TenantMixin


def _enum(e):
    return Enum(e, native_enum=False, values_callable=lambda x: [m.value for m in x])


class Alert(Base, TenantMixin, TimestampMixin):
    __tablename__ = "alert"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[AlertKind] = mapped_column(_enum(AlertKind), index=True)
    priority: Mapped[AlertPriority] = mapped_column(
        _enum(AlertPriority), default=AlertPriority.MEDIUM
    )
    status: Mapped[AlertStatus] = mapped_column(
        _enum(AlertStatus), default=AlertStatus.OPEN, index=True
    )

    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Règle déclencheuse lisible + seuil/valeur observée (auditabilité).
    rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Référence générique vers l'entité concernée (ex. product / invoice).
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run.id"), nullable=True
    )

    # Résolution humaine (audit) : qui, quand, note.
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
