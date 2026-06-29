"""Organisation (tenant = un commerce) + appartenance (membership) + invitation.

Le comptable peut être membre de plusieurs organisations via `Membership`.
Le modèle reste extensible pour le billing (hors scope) sans rien casser.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MembershipRole(enum.StrEnum):
    OWNER = "owner"  # tout (admin, billing, commandes)
    STAFF = "staff"  # opérations quotidiennes, pas d'admin/billing
    ACCOUNTANT = "accountant"  # lecture + factures/finance, PAS d'envoi commande
    READ_ONLY = "read_only"  # consultation


# Matrice de permissions par rôle (scopes). `*` = tous.
ROLE_PERMISSIONS: dict[MembershipRole, set[str]] = {
    MembershipRole.OWNER: {"*"},
    MembershipRole.STAFF: {"stocks", "invoices", "forecasts", "orders", "daily_entries"},
    MembershipRole.ACCOUNTANT: {"stocks", "invoices", "forecasts", "finance"},
    MembershipRole.READ_ONLY: {"stocks", "invoices", "forecasts", "read"},
}


class Organization(Base, TimestampMixin):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Métadonnées commerce (type d'activité) — utile pour la personnalisation.
    business_type: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Membership(Base, TimestampMixin):
    __tablename__ = "membership"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=MembershipRole.STAFF,
    )


class Invitation(Base, TimestampMixin):
    __tablename__ = "invitation"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organization.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=MembershipRole.STAFF,
    )
    # Jeton d'invitation (lien d'acceptation).
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    invited_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
