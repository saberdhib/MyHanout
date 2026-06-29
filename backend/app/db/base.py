"""Base déclarative SQLAlchemy 2.0 + métadonnées partagées.

NB : importer ce module garantit que tous les modèles sont enregistrés sur
`Base.metadata` (utile pour Alembic et la création des tables en test).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles."""


class TimestampMixin:
    """Colonnes created_at / updated_at automatiques."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
