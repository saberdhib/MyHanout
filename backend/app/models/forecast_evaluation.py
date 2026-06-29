"""Évaluation de prévision : écart prévu/réel (boucle MLOps).

Pour chaque produit/jour, on compare la demande PRÉVUE à la demande RÉELLE
(déduite des saisies de fin de journée) et on stocke l'erreur + le modèle utilisé.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ForecastEvaluation(Base, TimestampMixin):
    __tablename__ = "forecast_evaluation"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "eval_date", "model", name="uq_forecast_eval_product_date_model"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    eval_date: Mapped[date] = mapped_column(Date, index=True)

    predicted: Mapped[float] = mapped_column(Numeric(12, 2))
    actual: Mapped[float] = mapped_column(Numeric(12, 2))
    # Erreur absolue (|prévu-réel|) et pourcentage (|prévu-réel|/réel).
    error_abs: Mapped[float] = mapped_column(Numeric(12, 4))
    error_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)

    model: Mapped[str] = mapped_column(String(32))
    # Version du modèle ayant produit la prévision (traçabilité MLOps).
    model_version: Mapped[str] = mapped_column(String(64), default="v1")

    product: Mapped[Product] = relationship()
