"""Endpoints fidélité client : soldes, gain de points, échange de récompense."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.loyalty import (
    EarnRequest,
    LoyaltyAccountOut,
    LoyaltyDetailOut,
    RedeemResult,
)
from app.services import loyalty_service

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("", response_model=ListResponse[LoyaltyAccountOut])
async def list_loyalty(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ListResponse[LoyaltyAccountOut]:
    items = await loyalty_service.list_accounts(session)
    return ListResponse(items=items, total=len(items))


@router.get("/{customer_id}", response_model=LoyaltyDetailOut)
async def get_loyalty(
    customer_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> LoyaltyDetailOut:
    detail = await loyalty_service.account_detail(session, customer_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Aucun compte fidélité pour ce client")
    return detail


@router.post("/{customer_id}/earn", response_model=LoyaltyAccountOut)
async def earn_points(
    customer_id: int,
    body: EarnRequest,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("orders")),
) -> LoyaltyAccountOut:
    """Attribue les points d'un achat à un client (human-in-the-loop)."""
    account = await loyalty_service.earn(session, customer_id, body.amount, body.reason)
    if account is None:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return account


@router.post("/{customer_id}/redeem", response_model=RedeemResult)
async def redeem_reward(
    customer_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("orders")),
) -> RedeemResult:
    """Échange un palier de points contre la récompense (action validée par un humain)."""
    result = await loyalty_service.redeem(session, customer_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Aucun compte fidélité pour ce client")
    return result
