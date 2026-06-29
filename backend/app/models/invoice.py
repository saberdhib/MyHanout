"""Factures fournisseurs + lignes de facture (issues de l'OCR/ingestion)."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import InvoiceStatus, OcrStatus
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    from app.models.supplier import Supplier
    from app.models.user import User


class Invoice(Base, TenantMixin, TimestampMixin):
    __tablename__ = "invoice"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"), nullable=True)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=InvoiceStatus.PENDING,
    )
    ocr_status: Mapped[OcrStatus] = mapped_column(
        Enum(OcrStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=OcrStatus.NOT_STARTED,
    )
    # Chemin/URI du document source (PDF/photo).
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hash SHA-256 du fichier source : garantit l'idempotence (pas de doublon).
    file_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    # Rapport de validation métier (JSON sérialisé) : explique pourquoi en review.
    validation_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Confiance OCR (0..1) — sert à signaler une lecture peu fiable au réviseur.
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)

    # Piste de validation humaine (human-in-the-loop).
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier: Mapped[Supplier | None] = relationship(back_populates="invoices")
    reviewed_by: Mapped[User | None] = relationship()
    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
