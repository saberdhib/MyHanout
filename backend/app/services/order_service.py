"""Service commandes — human-in-the-loop sur la validation (stub)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.exceptions import ApprovalRequiredError, NotFoundError
from app.models.base import OrderStatus
from app.models.order import Order


async def approve_order(
    session: AsyncSession, order_id: int, *, user_id: int
) -> Order:
    """Valide une commande (action sensible : trace d'audit obligatoire)."""
    order = await session.get(Order, order_id)
    if not order:
        raise NotFoundError(f"Commande {order_id} introuvable")
    if order.status != OrderStatus.PENDING_APPROVAL:
        raise ApprovalRequiredError(
            f"Commande {order_id} non en attente de validation (statut={order.status})."
        )
    order.status = OrderStatus.APPROVED
    order.approved_by_id = user_id
    await record_audit(
        session,
        action="order.approve",
        user_id=user_id,
        resource="order",
        resource_id=order_id,
    )
    return order
