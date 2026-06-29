"""Endpoints commandes — suggestion, validation (3 modes), approbation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.order import (
    ConfirmOrderRequest,
    OrderLineOut,
    OrderOut,
    SuggestionOut,
    SuggestRequest,
)
from app.services.order_action_service import confirm_suggestion
from app.services.order_service import approve_order
from app.services.suggestion_service import suggest_orders

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_out(order) -> OrderOut:
    return OrderOut(
        id=order.id,
        supplier_id=order.supplier_id,
        status=str(order.status),
        action_mode=str(order.action_mode),
        total_amount=float(order.total_amount),
        supplier_message=order.supplier_message,
        lines=[
            OrderLineOut(
                product_id=line.product_id,
                quantity=float(line.quantity),
                unit_price=float(line.unit_price),
            )
            for line in order.lines
        ],
    )


@router.post("/suggest", response_model=SuggestionOut)
async def suggest(
    body: SuggestRequest,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("orders")),
) -> SuggestionOut:
    """Suggestion de commande explicable, déclenchée par le commerçant."""
    return await suggest_orders(
        session,
        horizon_days=body.horizon_days,
        horizon=body.horizon,
        product_ids=body.product_ids,
    )


@router.post("/confirm", response_model=OrderOut)
async def confirm(
    body: ConfirmOrderRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("orders")),
) -> OrderOut:
    """Valide une suggestion ajustée -> commande `confirmed` + action (3 modes)."""
    order = await confirm_suggestion(
        session,
        user_id=user.id,
        lines=body.lines,
        supplier_id=body.supplier_id,
        action_mode=body.action_mode,
    )
    await session.refresh(order, attribute_names=["lines"])
    return _order_out(order)


@router.post("/{order_id}/approve")
async def approve(
    order_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("orders")),
) -> dict:
    """Validation humaine d'une commande proposée par un agent (auditée)."""
    order = await approve_order(session, order_id, user_id=user.id)
    return {"id": order.id, "status": str(order.status), "approved_by": user.id}
