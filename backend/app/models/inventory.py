"""Snapshot de stock daté (matière du forecast + fraîcheur Data Ops).

`stock` porte la quantité **courante** ; `inventory_snapshot` capture l'état
**à une date** (point-in-time), produit par le pipeline d'ingestion. Sert à
mesurer la fraîcheur des données et à historiser le stock pour l'analyse.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class InventorySnapshot(Base, TenantMixin, TimestampMixin):
    __tablename__ = "inventory_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "product_id", "snapshot_date", name="uq_inventory_snapshot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run.id"), nullable=True
    )
