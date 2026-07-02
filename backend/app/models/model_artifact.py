"""Registre de modèles (MLOps) — versionne chaque modèle entraîné + ses métriques.

Chaque réentraînement (manuel, planifié, ou déclenché par la dérive) enregistre un
`ModelArtifact` versionné : paramètre entraîné (baseline du modèle naïf), métriques
d'erreur au moment de l'entraînement, déclencheur, et lien optionnel vers l'artefact
stocké (MinIO). Un seul artefact est **actif** par (produit, modèle).

Tenant (`TenantMixin`) : chaque commerce a ses propres modèles.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class RetrainTrigger(enum.StrEnum):
    MANUAL = "manual"  # déclenché à la main (bouton / API)
    SCHEDULED = "scheduled"  # cycle planifié (job pipeline)
    DRIFT = "drift"  # dérive de précision détectée (MAPE au-dessus du seuil)
    SEED = "seed"  # bootstrap (démo)


class ModelArtifact(Base, TenantMixin, TimestampMixin):
    __tablename__ = "model_artifact"

    id: Mapped[int] = mapped_column(primary_key=True)
    # product_id null = modèle global au commerce (rare) ; sinon par produit.
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("product.id"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(32), default="naive")  # naive|prophet|lgbm
    version: Mapped[str] = mapped_column(String(32), default="v1")

    # Paramètre « entraîné » du modèle naïf (moyenne mobile). Pour prophet/lgbm,
    # l'artefact sérialisé va dans artifact_uri (MinIO) ; baseline reste indicatif.
    baseline: Mapped[float] = mapped_column(Float, default=0.0)
    n_observations: Mapped[int] = mapped_column(Integer, default=0)

    # Métriques au moment de l'entraînement (traçabilité qualité).
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)

    trigger: Mapped[RetrainTrigger] = mapped_column(
        Enum(RetrainTrigger, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=RetrainTrigger.MANUAL,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Emplacement de l'artefact sérialisé (MinIO/S3) — null pour le modèle naïf.
    artifact_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
