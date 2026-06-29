"""Mixin multi-tenant : rattache une ligne à une organisation (commerce).

Toutes les tables métier héritent de `TenantMixin`. Le garde-fou central
(`app.core.tenancy`) filtre automatiquement les SELECT et estampille les INSERT
par l'organisation courante (issue du token, jamais du client).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class TenantMixin:
    """Ajoute `organization_id` (non nul, indexé) à un modèle métier."""

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), index=True, nullable=False
    )
