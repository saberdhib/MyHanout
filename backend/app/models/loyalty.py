"""Fidélité client (rétention) — compte de points + grand livre explicable.

Chaque client fidélisé a un `LoyaltyAccount` (solde + cumul à vie). Chaque mouvement
(gain sur achat, échange contre récompense, ajustement) est tracé dans
`LoyaltyTransaction` (explicabilité + audit). Tenant (`TenantMixin`).

Les ventes de caisse ne sont pas nominatives : l'attribution de points est une action
**explicite** du commerçant (human-in-the-loop), pas un calcul automatique.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class LoyaltyTxnKind(enum.StrEnum):
    EARN = "earn"  # points gagnés sur un achat
    REDEEM = "redeem"  # points échangés contre une récompense
    ADJUST = "adjust"  # correction manuelle (geste commercial, erreur)


class LoyaltyAccount(Base, TenantMixin, TimestampMixin):
    __tablename__ = "loyalty_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), unique=True, index=True)
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0)  # cumul (jamais décrémenté)


class LoyaltyTransaction(Base, TenantMixin, TimestampMixin):
    __tablename__ = "loyalty_transaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("loyalty_account.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), index=True)
    kind: Mapped[LoyaltyTxnKind] = mapped_column(
        Enum(LoyaltyTxnKind, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        index=True,
    )
    points: Mapped[int] = mapped_column(Integer)  # +gain / -échange
    # Montant d'achat à l'origine du gain (explicabilité), nullable.
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(String(255))  # explication humaine
