"""Fixtures de test : base sqlite en mémoire + client FastAPI.

IMPORTANT : on force DATABASE_URL en sqlite AVANT tout import applicatif pour
éviter le chargement du driver asyncpg (postgres) et travailler hors docker.
"""

from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///file:test?mode=memory&cache=shared&uri=true"
)
os.environ.setdefault("ENV", "local")

import asyncio
import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models as m
from app.core.deps import get_db
from app.main import app

# Engine de test partagé (cache=shared garde les tables entre connexions).
_engine = create_async_engine("sqlite+aiosqlite:///file:test?mode=memory&cache=shared&uri=true")
TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(m.Base.metadata.create_all)
    async with TestSession() as s:
        sup = m.Supplier(name="Boucherie Centrale", payment_terms_days=30)
        prod = m.Product(
            sku="BOEUF-HACHE",
            name="Boeuf haché",
            unit="kg",
            unit_price=95,
            perishable=True,
            shelf_life_days=3,
            supplier=sup,
        )
        s.add_all([sup, prod])
        await s.flush()
        # Stock sous le seuil -> doit apparaître dans /stocks/alerts.
        s.add(m.Stock(product_id=prod.id, quantity=5, reorder_threshold=10))
        for d in range(40):
            day = datetime.datetime(2026, 5, 1) + datetime.timedelta(days=d)
            qty = 10 + d % 5
            s.add(
                m.Sale(
                    product_id=prod.id,
                    quantity=qty,
                    unit_price=95,
                    total=qty * 95,
                    sold_at=day,
                )
            )
        inv = m.Invoice(number="FAC-1", supplier=sup, currency="EUR", total_amount=100)
        inv.lines.append(
            m.InvoiceLine(
                product_id=prod.id, description="x", quantity=1, unit_price=100, line_total=100
            )
        )
        s.add(inv)
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    asyncio.get_event_loop().run_until_complete(_init_db())
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    async def override_db():
        async with TestSession() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
