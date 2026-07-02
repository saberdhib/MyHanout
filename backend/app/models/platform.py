"""Plan « plateforme » (backoffice MyHanout) — GLOBAL, NON tenant.

⚠️ Ces tables sont l'**inverse** du garde-fou multi-tenant : elles permettent à
l'opérateur (MyHanout) de gérer *tous* les commerces. Elles n'héritent donc PAS de
`TenantMixin` (aucune colonne `organization_id`, aucun filtrage automatique). Tout
accès cross-tenant passe par `get_platform_admin` et est **audité** (`audit_log`).

- `PlatformAdmin` : un opérateur MyHanout (superadmin | support | billing).
- `Subscription` : la réalité commerciale d'un commerce (plan, MRR, période).

Le *statut de cycle de vie* d'un commerce (qui contrôle l'accès) vit sur
`Organization.status` — voir `app/models/organization.py`.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PlatformRole(enum.StrEnum):
    SUPERADMIN = "superadmin"  # tout (provisioning, suspension, billing, impersonation)
    SUPPORT = "support"  # vue 360 + tickets + impersonation, PAS de billing/suspension
    BILLING = "billing"  # vue 360 + abonnements/plans, PAS de suspension


# Scopes par rôle plateforme. `*` = tous.
PLATFORM_ROLE_PERMISSIONS: dict[PlatformRole, set[str]] = {
    PlatformRole.SUPERADMIN: {"*"},
    PlatformRole.SUPPORT: {"clients:read", "tickets", "impersonate"},
    PlatformRole.BILLING: {"clients:read", "billing"},
}


class Plan(enum.StrEnum):
    TRIAL = "trial"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


def _enum(e: type[enum.Enum]) -> Enum:
    """Enum stocké en minuscules (cohérent migration/seed, cf. CLAUDE.md §6)."""
    return Enum(e, native_enum=False, values_callable=lambda x: [m.value for m in x])


class PlatformAdmin(Base, TimestampMixin):
    """Opérateur MyHanout (staff plateforme). Global, hors garde-fou tenant."""

    __tablename__ = "platform_admin"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    role: Mapped[PlatformRole] = mapped_column(_enum(PlatformRole), default=PlatformRole.SUPPORT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base, TimestampMixin):
    """Abonnement commercial d'un commerce (facturation). Un par organisation."""

    __tablename__ = "subscription"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), unique=True, index=True
    )
    plan: Mapped[Plan] = mapped_column(_enum(Plan), default=Plan.TRIAL)
    status: Mapped[SubscriptionStatus] = mapped_column(
        _enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING
    )
    # MRR contractuel (€) — pour le pilotage (ARR, churn) côté backoffice.
    mrr_eur: Mapped[float] = mapped_column(Float, default=0.0)
    # Dates de cycle (ISO, nullable). Simples : le billing réel (Stripe) est hors scope.
    trial_ends_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    started_on: Mapped[str | None] = mapped_column(String(10), nullable=True)
    current_period_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
