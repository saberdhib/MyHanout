"""Tests d'intégration contre un vrai PostgreSQL 16 + pgvector.

Exécutés uniquement si `INTEGRATION_DATABASE_URL` est défini (job CI dédié avec
un service postgres). En local/CI par défaut (sqlite, sans clé), ils sont skippés
— le parcours mock reste 100 % vert sans dépendance externe.

Prérequis : les migrations Alembic ont déjà tourné sur la base cible
(`alembic upgrade head`), ce qui crée aussi l'extension pgvector et document_chunk.
"""

from __future__ import annotations

import datetime
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

INTEGRATION_URL = os.getenv("INTEGRATION_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not INTEGRATION_URL, reason="INTEGRATION_DATABASE_URL non défini"),
]


@pytest.fixture
def pg_session():
    engine = create_async_engine(INTEGRATION_URL)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield Session
    # Pas de dispose async ici : engine GC en fin de process.


@pytest.mark.asyncio
async def test_pgvector_extension_present(pg_session):
    async with pg_session() as s:
        version = await s.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        assert version is not None


@pytest.mark.asyncio
async def test_invoice_enum_roundtrip_on_pg(pg_session):
    """Vérifie le stockage des enums en valeur minuscule (values_callable)."""
    from app.models.base import InvoiceStatus
    from app.models.invoice import Invoice

    async with pg_session() as s:
        inv = Invoice(
            number=f"IT-{datetime.datetime.now(datetime.UTC).timestamp()}",
            currency="EUR",
            status=InvoiceStatus.PENDING_REVIEW,
        )
        s.add(inv)
        await s.commit()
        raw = await s.scalar(text("SELECT status FROM invoice WHERE id = :id"), {"id": inv.id})
        assert raw == "pending_review"


@pytest.mark.asyncio
async def test_forecast_service_on_pg(pg_session):
    """Pipeline data->modèle sur vrai PG : seed minimal puis prévision."""
    from app.models.product import Product
    from app.models.sale import Sale
    from app.services.forecast_service import forecast_product

    async with pg_session() as s:
        product = Product(sku=f"IT-{id(s)}", name="Test", unit="kg")
        s.add(product)
        await s.flush()
        base = datetime.datetime(2026, 5, 1)
        for d in range(30):
            s.add(
                Sale(
                    product_id=product.id,
                    quantity=10,
                    unit_price=5,
                    total=50,
                    sold_at=base + datetime.timedelta(days=d),
                )
            )
        await s.commit()
        result = await forecast_product(s, product.id, horizon_days=7)
        assert result.model == "naive"
        assert len(result.points) == 7
