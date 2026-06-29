"""Couche financière : référentiel de catégories + retours de classification.

`ExpenseCategory` est un **référentiel global** (PAS `TenantMixin`) : c'est une
taxonomie standard de charges (téléphonie, énergie, loyer…), identique pour tous
les commerces, sans donnée personnelle. La rattacher à un tenant n'apporterait
que de la duplication. Le garde-fou central ne filtre que les tables `TenantMixin`
— une table de lookup globale est donc naturellement partagée (lecture seule).

`ExpenseClassificationFeedback` est en revanche **tenant-scopé** : il trace les
corrections humaines (signal d'apprentissage) propres à chaque commerce.
"""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import ClassificationSource, ExpenseKind
from app.models.tenant import TenantMixin


def _enum_col(enum_cls):
    return Enum(enum_cls, native_enum=False, values_callable=lambda e: [m.value for m in e])


class ExpenseCategory(Base, TimestampMixin):
    """Catégorie de charge (référentiel global, lecture seule côté métier)."""

    __tablename__ = "expense_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128))
    kind: Mapped[ExpenseKind] = mapped_column(_enum_col(ExpenseKind), default=ExpenseKind.OPEX)
    # Indice de rattachement comptable (ex. compte 6xx/2xx) — optionnel, indicatif.
    accounting_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ExpenseClassificationFeedback(Base, TenantMixin, TimestampMixin):
    """Correction humaine d'une classification (signal d'apprentissage, tenant)."""

    __tablename__ = "expense_classification_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"), index=True)
    previous_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_category.id"), nullable=True
    )
    new_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_category.id"), nullable=True
    )
    previous_kind: Mapped[ExpenseKind | None] = mapped_column(_enum_col(ExpenseKind), nullable=True)
    new_kind: Mapped[ExpenseKind | None] = mapped_column(_enum_col(ExpenseKind), nullable=True)
    # Source remplacée (typiquement "ai") — pour mesurer la qualité du classifieur.
    previous_source: Mapped[ClassificationSource | None] = mapped_column(
        _enum_col(ClassificationSource), nullable=True
    )
    corrected_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
