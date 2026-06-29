"""Historique des prix (achat/vente) par produit, dans le temps — tenant-scopé.

Permet de tracer l'évolution des prix (courbe) et d'expliquer les marges/anomalies.
On écrit une ligne à chaque changement constaté (import, vente, saisie).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import PriceKind
from app.models.tenant import TenantMixin


class PriceHistory(Base, TenantMixin, TimestampMixin):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    kind: Mapped[PriceKind] = mapped_column(
        Enum(PriceKind, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        index=True,
    )
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Origine de l'observation (import, sale, manual, invoice…).
    source: Mapped[str] = mapped_column(String(32), default="manual")
