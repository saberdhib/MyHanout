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
from sqlalchemy import select, text
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


async def _demo_org_id(session) -> int:
    """Org 'demo' créée par le seed (lancé avant les tests dans le job CI)."""
    from app.models.organization import Organization

    org = await session.scalar(select(Organization).where(Organization.slug == "demo"))
    assert org is not None, "Lancer `python -m app.db.seed` avant les tests d'intégration"
    return org.id


@pytest.mark.asyncio
async def test_invoice_enum_roundtrip_on_pg(pg_session):
    """Vérifie le stockage des enums en valeur minuscule (values_callable)."""
    from app.core.tenancy import tenant_context
    from app.models.base import InvoiceStatus
    from app.models.invoice import Invoice

    async with pg_session() as s:
        org_id = await _demo_org_id(s)
        with tenant_context(org_id):
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
    """Pipeline data->modèle sur vrai PG : seed minimal puis prévision (tenant)."""
    from app.core.tenancy import tenant_context
    from app.models.product import Product
    from app.models.sale import Sale
    from app.services.forecast_service import forecast_product

    async with pg_session() as s:
        org_id = await _demo_org_id(s)
        with tenant_context(org_id):
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


@pytest.mark.asyncio
async def test_rls_blocks_raw_sql_cross_tenant(pg_session):
    """RLS Postgres (defense-in-depth) : même en SQL BRUT (hors garde-fou ORM),
    une session scopée sur une org ne voit pas les lignes d'une autre org.

    Prérequis : migration 0025 appliquée (alembic upgrade head)."""
    from app.core.tenancy import tenant_context
    from app.models.organization import Organization
    from app.models.product import Product

    async with pg_session() as s:
        # Vérifie que la RLS est bien active (sinon test non pertinent).
        rls_on = await s.scalar(
            text("SELECT relrowsecurity FROM pg_class WHERE relname = 'product'")
        )
        if not rls_on:
            pytest.skip("RLS non active (migration 0025 non appliquée)")

        demo_id = await _demo_org_id(s)
        # Crée une seconde org + un produit qui lui appartient (GUC non posé => accès
        # complet, l'ORM estampille l'org via tenant_context).
        other = Organization(name="RLS Other", slug=f"rls-{id(s)}")
        s.add(other)
        await s.flush()
        with tenant_context(other.id):
            p = Product(sku=f"RLS-{id(s)}", name="RLS", unit="kg")
            s.add(p)
            await s.flush()
            other_pid = p.id
        await s.commit()

        # Scope RLS sur l'org démo : le produit de l'autre org est INVISIBLE en SQL brut.
        await s.execute(
            text("SELECT set_config('app.current_org', :v, false)"), {"v": str(demo_id)}
        )
        visible = await s.scalar(
            text("SELECT count(*) FROM product WHERE id = :id"), {"id": other_pid}
        )
        assert visible == 0  # RLS bloque, même sans garde-fou ORM

        # Scope sur l'autre org : le produit redevient visible.
        await s.execute(
            text("SELECT set_config('app.current_org', :v, false)"), {"v": str(other.id)}
        )
        visible = await s.scalar(
            text("SELECT count(*) FROM product WHERE id = :id"), {"id": other_pid}
        )
        assert visible == 1

        # WITH CHECK : insérer une ligne pour une AUTRE org que le scope courant échoue.
        await s.execute(
            text("SELECT set_config('app.current_org', :v, false)"), {"v": str(demo_id)}
        )
        from sqlalchemy.exc import DBAPIError

        with pytest.raises(DBAPIError):  # violation RLS WITH CHECK
            await s.execute(
                text(
                    "INSERT INTO supplier (organization_id, name, created_at, updated_at) "
                    "VALUES (:org, 'illegal', now(), now())"
                ),
                {"org": other.id},
            )
        await s.rollback()


@pytest.mark.asyncio
async def test_pgvector_store_roundtrip(pg_session):
    """RAG sur vrai pgvector : insertion vector(1536) + recherche cosine, tenant."""
    from app.core.tenancy import tenant_context
    from app.intelligence.rag.embeddings import MockEmbeddingProvider
    from app.intelligence.rag.store import PgVectorStore

    embedder = MockEmbeddingProvider()
    store = PgVectorStore()
    async with pg_session() as s:
        org_id = await _demo_org_id(s)
        with tenant_context(org_id):
            await store.add(
                s,
                organization_id=org_id,
                invoice_id=None,
                content="facture boeuf haché",
                embedding=embedder.embed("facture boeuf haché"),
            )
            await s.commit()
            res = await store.search(
                s, organization_id=org_id, embedding=embedder.embed("boeuf"), k=3
            )
            assert res and "boeuf" in res[0].content
