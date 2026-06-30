"""Run de pipeline data : orchestration explicite, observable et traçable.

Chaque exécution d'un job (ingestion, feature engineering, forecast, reco…)
crée un `PipelineRun`. Les données produites (recommandations, snapshots)
référencent le `pipeline_run_id` qui les a générées → traçabilité bout-en-bout
(« quel run a produit cette reco, avec quelle fraîcheur de données »).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import PipelineStatus, PipelineTrigger
from app.models.tenant import TenantMixin


def _enum(e):  # Enum stocké en minuscules (cohérent migration/seed).
    return Enum(e, native_enum=False, values_callable=lambda x: [m.value for m in x])


class PipelineRun(Base, TenantMixin, TimestampMixin):
    __tablename__ = "pipeline_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[PipelineStatus] = mapped_column(
        _enum(PipelineStatus), default=PipelineStatus.PENDING, index=True
    )
    trigger: Mapped[PipelineTrigger] = mapped_column(
        _enum(PipelineTrigger), default=PipelineTrigger.MANUAL
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Horodatage de la donnée la plus fraîche traitée par ce run (fraîcheur data).
    data_freshness_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Auteur du déclenchement manuel (human-in-the-loop), si applicable.
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    # Détails libres (JSON sérialisé) : compteurs par asset, paramètres…
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
