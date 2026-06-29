"""Boucherie : achat d'une bête au poids → décomposition en pièces → traçabilité.

Modèle métier spécifique : on achète une « bête » (demi-bœuf, agneau entier…) à un
poids et un coût ; on la **désosse / découpe** en pièces dont le poids réel diffère
du prévu ; on **alloue le coût** au kilo réellement valorisable ; on garde la
**traçabilité** (lot → fournisseur → date) exigée pour la viande.

Les NOMS de coupes (aloyau, av5, etc.) restent du **texte libre configurable** :
le modèle ne fige aucun vocabulaire métier.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import MeatLotStatus, MeatSpecies
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    from app.models.supplier import Supplier


def _enum(e):
    return Enum(e, native_enum=False, values_callable=lambda x: [m.value for m in x])


class MeatLot(Base, TenantMixin, TimestampMixin):
    """Une bête achetée au poids (unité de traçabilité)."""

    __tablename__ = "meat_lot"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Code de traçabilité (étiquette sanitaire / lot fournisseur).
    lot_code: Mapped[str] = mapped_column(String(64), index=True)
    species: Mapped[MeatSpecies] = mapped_column(_enum(MeatSpecies), default=MeatSpecies.BOEUF)
    label: Mapped[str] = mapped_column(String(128))  # ex. "demi-bœuf", "agneau entier"
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    gross_weight_kg: Mapped[float] = mapped_column(Numeric(10, 3))
    purchase_cost: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[MeatLotStatus] = mapped_column(
        _enum(MeatLotStatus), default=MeatLotStatus.RECEIVED
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier: Mapped[Supplier | None] = relationship()
    cuts: Mapped[list[MeatCut]] = relationship(back_populates="lot", cascade="all, delete-orphan")


class MeatCut(Base, TenantMixin, TimestampMixin):
    """Une pièce issue d'un lot (prévu vs réel, os/perte, lien produit optionnel)."""

    __tablename__ = "meat_cut"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("meat_lot.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"), nullable=True)
    cut_label: Mapped[str] = mapped_column(String(128))  # vocabulaire libre (aloyau, av5…)
    expected_weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    actual_weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    # Os / perte / chute : exclu du poids valorisable pour l'allocation de coût.
    is_waste: Mapped[bool] = mapped_column(Boolean, default=False)

    lot: Mapped[MeatLot] = relationship(back_populates="cuts")
