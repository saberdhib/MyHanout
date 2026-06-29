"""Endpoints commandes — action sensible (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.core.security import CurrentUser
from app.services.order_service import approve_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/{order_id}/approve")
async def approve(
    order_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    _: object = Depends(require_permission("orders")),
) -> dict:
    """Validation humaine d'une commande proposée par un agent (auditée)."""
    order = await approve_order(session, order_id, user_id=user.id)
    return {"id": order.id, "status": order.status, "approved_by": user.id}
