"""Recommandation de réassort persistée, explicable et traçable.

Issue d'un forecast + d'un snapshot stock, produite par un `PipelineRun`
(traçabilité : `pipeline_run_id` + `model_version`). Chaque reco porte sa
quantité suggérée, sa confiance, son facteur de risque, son score final, son
**explication humaine** et les **données utilisées** (JSON) — pour audit.

Human-in-the-loop : statut `suggested` → action humaine → `accepted`/`dismissed`.
"""

from __future__ import annotations

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import RecommendationStatus
from app.models.tenant import TenantMixin


class Recommendation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "recommendation"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run.id"), nullable=True, index=True
    )
    model_version: Mapped[str] = mapped_column(String(64), default="v1")

    # action lisible : order | reduce | hold (cf. moteur de règles).
    action: Mapped[str] = mapped_column(String(16), default="order")
    suggested_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    horizon_days: Mapped[int] = mapped_column(Integer, default=7)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1
    risk_factor: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1 (risque rupture)
    score: Mapped[float] = mapped_column(Float, default=0.0)  # priorité (tri)

    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(
            RecommendationStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=RecommendationStatus.SUGGESTED,
        index=True,
    )
    explanation: Mapped[str] = mapped_column(Text)  # raison humaine (explicabilité)
    data_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON des entrées
