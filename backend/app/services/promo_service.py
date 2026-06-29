"""Promos flash : détecte les produits en fin de vie → propose une promo IA
explicable → publication validée par l'humain (réseaux + clients opt-in).

C'est le moment « valeur » : viande/pommes en fin de vie → 💥 promo ciblée,
enrichie par les signaux (météo, tendances), publiée sous contrôle humain.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.intelligence.imaging import get_image_provider
from app.intelligence.llm import LLMMessage, get_llm_provider
from app.intelligence.signals import get_signals
from app.messaging.publish import get_channels
from app.models.base import CampaignStatus
from app.models.product import Product
from app.models.promo import PromoCampaign
from app.repositories.stock import StockRepository

log = get_logger(__name__)

_DEFAULT_DISCOUNT = 30.0


async def scan_expiring(
    session: AsyncSession, *, organization_id: int, within_days: int = 3
) -> list[PromoCampaign]:
    """Propose (sans publier) une promo par produit proche de la péremption."""
    stocks = await StockRepository(session).list_expiring(within_days=within_days)
    signals = get_signals()
    llm = get_llm_provider()
    campaigns: list[PromoCampaign] = []

    for stock in stocks:
        product = stock.product
        name = product.name if product else "produit"
        reason = (
            f"Stock « {name} » périme le {stock.expiry_date} (≤ {within_days} j). "
            f"Météo : {signals.weather.condition} {signals.weather.temp_c:g}°C "
            f"({signals.weather.demand_hint}). Tendance : {signals.trends[0].topic}."
        )
        system = (
            "Tu rédiges un court message de promo commerçant "
            "(1-2 phrases, emoji, ton chaleureux)."
        )
        user = f"Promo -{_DEFAULT_DISCOUNT:g}% sur « {name} » (fin de vie). Contexte: {reason}"
        resp = await llm.complete(
            [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]
        )
        campaign = PromoCampaign(
            product_id=product.id if product else None,
            title=f"Promo flash — {name}",
            message=resp.content,
            discount_pct=_DEFAULT_DISCOUNT,
            reason=reason,
            status=CampaignStatus.DRAFT,
        )
        session.add(campaign)
        campaigns.append(campaign)

    await session.flush()
    await record_audit(
        session,
        action="promo.scan",
        resource="promo_campaign",
        detail=f"proposed={len(campaigns)} within_days={within_days}",
    )
    log.info("promo.scan", organization_id=organization_id, proposed=len(campaigns))
    return campaigns


def _build_visual_prompt(product_name: str, discount_pct: float) -> str:
    """Construit un prompt text-to-image explicable pour l'affiche promo."""
    return (
        f"Affiche promotionnelle commercant de quartier : -{discount_pct:g}% sur "
        f"« {product_name} ». Style chaleureux, anti-gaspillage, lumineux, appetissant, "
        f"typographie moderne, vert et orange."
    )


async def generate_visual(
    session: AsyncSession, *, campaign_id: int, user_id: int | None
) -> PromoCampaign:
    """Génère une affiche promo (visuel) pour une campagne — human-in-the-loop.

    Le visuel est un brouillon attaché à la campagne ; rien n'est publié ici. Le
    prompt est conservé (`visual_prompt`) pour la traçabilité/explicabilité.
    """
    campaign = await session.get(PromoCampaign, campaign_id)
    if not campaign:
        raise NotFoundError(f"Campagne {campaign_id} introuvable")

    product_name = "produit"
    if campaign.product_id:
        product = await session.get(Product, campaign.product_id)
        if product:
            product_name = product.name

    prompt = _build_visual_prompt(product_name, float(campaign.discount_pct or 0))
    image = await get_image_provider().generate(prompt)
    campaign.visual_url = image.data_url
    campaign.visual_prompt = prompt
    await record_audit(
        session,
        action="promo.visual",
        user_id=user_id,
        resource="promo_campaign",
        resource_id=campaign.id,
        detail=f"provider={image.provider} media={image.media_type}",
    )
    log.info("promo.visual", campaign_id=campaign.id, provider=image.provider)
    return campaign


async def publish_campaign(
    session: AsyncSession,
    *,
    campaign_id: int,
    channels: list[str],
    user_id: int | None,
) -> PromoCampaign:
    """Publie une promo validée par l'humain sur les canaux choisis (audité)."""
    campaign = await session.get(PromoCampaign, campaign_id)
    if not campaign:
        raise NotFoundError(f"Campagne {campaign_id} introuvable")
    if campaign.status == CampaignStatus.PUBLISHED:
        raise AppError("Campagne déjà publiée", code="already_published")

    org_id = campaign.organization_id
    delivered = 0
    for channel in get_channels(channels):
        result = await channel.publish(session, organization_id=org_id, message=campaign.message)
        delivered += result.delivered

    campaign.status = CampaignStatus.PUBLISHED
    campaign.channels = ",".join(channels)
    campaign.audience_count = delivered
    campaign.published_at = datetime.now(UTC)
    await record_audit(
        session,
        action="promo.publish",
        user_id=user_id,
        resource="promo_campaign",
        resource_id=campaign.id,
        detail=f"channels={channels} delivered={delivered}",
    )
    log.info("promo.published", campaign_id=campaign.id, delivered=delivered)
    return campaign
