"""Ingestion des ventes depuis la caisse (POS) — idempotent, tenant-scopé.

Le connecteur (mock keyless par défaut) fournit des tickets ; on insère les
ventes manquantes (clé d'idempotence : `external_ref`). Les ventes sans produit
connu sont ignorées (comptabilisées comme « skipped »). Réutilisable par un poll
ou par un webhook.
"""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.logging import get_logger
from app.ingestion.pos import POSSale, get_pos_connector
from app.models.product import Product
from app.models.sale import Sale

log = get_logger(__name__)


class POSSyncResult(BaseModel):
    provider: str
    inserted: int = 0
    duplicates: int = 0
    skipped_unknown_sku: int = 0


async def ingest_pos_sales(
    session: AsyncSession, sales: list[POSSale], *, provider: str, user_id: int | None = None
) -> POSSyncResult:
    """Insère les ventes caisse manquantes (idempotent par external_ref)."""
    result = POSSyncResult(provider=provider)
    for s in sales:
        existing = await session.scalar(select(Sale.id).where(Sale.external_ref == s.external_ref))
        if existing:
            result.duplicates += 1
            continue
        product = await session.scalar(select(Product).where(Product.sku == s.sku.upper()))
        if product is None:
            result.skipped_unknown_sku += 1
            continue
        session.add(
            Sale(
                product_id=product.id,
                quantity=s.quantity,
                unit_price=s.unit_price,
                total=s.quantity * s.unit_price,
                sold_at=s.sold_at,
                external_ref=s.external_ref,
            )
        )
        result.inserted += 1
    await session.flush()
    await record_audit(
        session,
        action="pos.sync",
        user_id=user_id,
        resource="sale",
        detail=(
            f"provider={provider} inserted={result.inserted} dup={result.duplicates} "
            f"skipped={result.skipped_unknown_sku}"
        ),
    )
    log.info("pos.sync", **result.model_dump())
    return result


async def sync_from_connector(
    session: AsyncSession, *, user_id: int | None = None, limit: int = 50
) -> POSSyncResult:
    """Poll le connecteur caisse configuré puis ingère les ventes."""
    connector = get_pos_connector()
    sales = await connector.fetch_sales(limit=limit)
    return await ingest_pos_sales(session, sales, provider=connector.name, user_id=user_id)
