"""Service fidélité : gain de points, échange de récompense, soldes & historique.

Human-in-the-loop : l'attribution de points (achat) et l'échange (récompense) sont des
actions explicites du commerçant. Chaque mouvement est tracé (grand livre) → explicable.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError
from app.intelligence.loyalty.engine import points_for_amount, reward_status
from app.models.customer import Customer
from app.models.loyalty import LoyaltyAccount, LoyaltyTransaction, LoyaltyTxnKind
from app.schemas.loyalty import (
    LoyaltyAccountOut,
    LoyaltyDetailOut,
    LoyaltyTxnOut,
    RedeemResult,
)


async def _account_for(session: AsyncSession, customer_id: int) -> LoyaltyAccount | None:
    return await session.scalar(
        select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id)
    )


async def get_or_create_account(session: AsyncSession, customer_id: int) -> LoyaltyAccount | None:
    """Compte fidélité du client (créé à la volée). None si le client n'existe pas (org)."""
    customer = await session.get(Customer, customer_id)  # filtré par le garde-fou tenant
    if customer is None:
        return None
    account = await _account_for(session, customer_id)
    if account is None:
        account = LoyaltyAccount(customer_id=customer_id, points_balance=0, lifetime_points=0)
        session.add(account)
        await session.flush()
    return account


def _status_out(account: LoyaltyAccount, customer_name: str | None) -> LoyaltyAccountOut:
    st = reward_status(
        account.points_balance, settings.loyalty_reward_threshold, settings.loyalty_reward_label
    )
    return LoyaltyAccountOut(
        customer_id=account.customer_id,
        customer_name=customer_name,
        points_balance=account.points_balance,
        lifetime_points=account.lifetime_points,
        reward_ready=st.reward_ready,
        points_to_next=st.points_to_next,
        rewards_available=st.rewards_available,
        explanation=st.explanation,
    )


async def earn(
    session: AsyncSession, customer_id: int, amount: float, reason: str | None = None
) -> LoyaltyAccountOut | None:
    """Crédite les points d'un achat (arrondi bas) + trace le mouvement."""
    account = await get_or_create_account(session, customer_id)
    if account is None:
        return None
    pts = points_for_amount(amount, settings.loyalty_points_per_euro)
    account.points_balance += pts
    account.lifetime_points += pts
    session.add(
        LoyaltyTransaction(
            account_id=account.id,
            customer_id=customer_id,
            kind=LoyaltyTxnKind.EARN,
            points=pts,
            amount=amount,
            reason=reason or f"Achat {amount:.2f} € → {pts} pts",
        )
    )
    await session.commit()
    customer = await session.get(Customer, customer_id)
    return _status_out(account, customer.name if customer else None)


async def redeem(session: AsyncSession, customer_id: int) -> RedeemResult | None:
    """Échange un palier de points contre la récompense (human-in-the-loop)."""
    account = await _account_for(session, customer_id)
    if account is None:
        return None
    threshold = settings.loyalty_reward_threshold
    if account.points_balance < threshold:
        raise AppError(
            f"Solde insuffisant : {account.points_balance}/{threshold} pts pour une récompense."
        )
    account.points_balance -= threshold
    label = settings.loyalty_reward_label
    session.add(
        LoyaltyTransaction(
            account_id=account.id,
            customer_id=customer_id,
            kind=LoyaltyTxnKind.REDEEM,
            points=-threshold,
            amount=None,
            reason=f"Échange contre « {label} »",
        )
    )
    await session.commit()
    bal = account.points_balance
    return RedeemResult(
        customer_id=customer_id,
        reward_label=label,
        points_spent=threshold,
        points_balance=bal,
        explanation=f"« {label} » remis au client (−{threshold} pts). Solde : {bal} pts.",
    )


async def list_accounts(session: AsyncSession) -> list[LoyaltyAccountOut]:
    accounts = list(
        await session.scalars(select(LoyaltyAccount).order_by(LoyaltyAccount.points_balance.desc()))
    )
    names = {c.id: c.name for c in await session.scalars(select(Customer))}
    return [_status_out(a, names.get(a.customer_id)) for a in accounts]


async def account_detail(session: AsyncSession, customer_id: int) -> LoyaltyDetailOut | None:
    account = await _account_for(session, customer_id)
    if account is None:
        return None
    customer = await session.get(Customer, customer_id)
    txns = list(
        await session.scalars(
            select(LoyaltyTransaction)
            .where(LoyaltyTransaction.customer_id == customer_id)
            .order_by(LoyaltyTransaction.id.desc())
        )
    )
    base = _status_out(account, customer.name if customer else None)
    return LoyaltyDetailOut(
        **base.model_dump(),
        transactions=[
            LoyaltyTxnOut(
                id=t.id,
                kind=str(t.kind),
                points=t.points,
                amount=t.amount,
                reason=t.reason,
                created_at=t.created_at.isoformat() if t.created_at else None,
            )
            for t in txns
        ],
    )
