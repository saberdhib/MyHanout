"""Endpoints promos flash (proposition IA + publication human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser
from app.models.promo import PromoCampaign
from app.schemas.common import ListResponse
from app.services.promo_service import generate_visual, publish_campaign, scan_expiring

router = APIRouter(prefix="/promos", tags=["promos"])


class PromoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None = None
    title: str
    message: str
    discount_pct: float
    reason: str | None = None
    status: str
    channels: str | None = None
    audience_count: int
    visual_url: str | None = None
    visual_prompt: str | None = None


class PublishRequest(BaseModel):
    channels: list[str] = ["social", "customers"]


def _org(user: CurrentUser) -> int:
    if user.organization_id is None:
        raise PermissionDeniedError("Aucune organisation active")
    return user.organization_id


@router.post("/scan", response_model=ListResponse[PromoOut])
async def scan(
    within_days: int = 3,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("marketing")),
) -> ListResponse[PromoOut]:
    """Détecte les produits en fin de vie et propose des promos (brouillons)."""
    campaigns = await scan_expiring(session, organization_id=_org(user), within_days=within_days)
    items = [PromoOut.model_validate(c) for c in campaigns]
    return ListResponse(items=items, total=len(items))


@router.get("", response_model=ListResponse[PromoOut])
async def list_promos(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("marketing")),
) -> ListResponse[PromoOut]:
    rows = list(
        (await session.scalars(select(PromoCampaign).order_by(PromoCampaign.id.desc()))).all()
    )
    items = [PromoOut.model_validate(c) for c in rows]
    return ListResponse(items=items, total=len(items))


@router.post("/{campaign_id}/visual", response_model=PromoOut)
async def visual(
    campaign_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("marketing")),
) -> PromoOut:
    """Génère une affiche promo (brouillon) pour la campagne (human-in-the-loop)."""
    campaign = await generate_visual(session, campaign_id=campaign_id, user_id=user.id)
    return PromoOut.model_validate(campaign)


@router.post("/{campaign_id}/publish", response_model=PromoOut)
async def publish(
    campaign_id: int,
    body: PublishRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("marketing")),
) -> PromoOut:
    """Publie une promo validée sur les canaux choisis (réseaux + clients opt-in)."""
    campaign = await publish_campaign(
        session, campaign_id=campaign_id, channels=body.channels, user_id=user.id
    )
    return PromoOut.model_validate(campaign)
