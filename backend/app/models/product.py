"""Produits du catalogue commerçant."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(32), default="unit")  # kg, unit, L...
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Gestion de la péremption.
    perishable: Mapped[bool] = mapped_column(Boolean, default=False)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier.id"), nullable=True
    )
    supplier: Mapped["Supplier | None"] = relationship(back_populates="products")  # noqa: F821

    stocks: Mapped[list["Stock"]] = relationship(back_populates="product")  # noqa: F821
    sales: Mapped[list["Sale"]] = relationship(back_populates="product")  # noqa: F821
