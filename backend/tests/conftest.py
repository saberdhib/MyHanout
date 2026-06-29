"""Fixtures de test : base sqlite en mémoire + client FastAPI (multi-tenant).

IMPORTANT : on force DATABASE_URL en sqlite AVANT tout import applicatif pour
éviter le chargement du driver asyncpg (postgres) et travailler hors docker.

Deux organisations sont seedées (A et B) pour permettre le test d'isolation.
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
from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.main import app
from app.models.organization import MembershipRole

_engine = create_async_engine("sqlite+aiosqlite:///file:test?mode=memory&cache=shared&uri=true")
TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _seed_org_products(session: AsyncSession, org_id: int, sku: str, *, with_history: bool):
    """Crée un produit + stock (+ ventes/facture) dans une org donnée."""
    with tenant_context(org_id):
        sup = m.Supplier(name=f"Fournisseur {org_id}", payment_terms_days=30)
        prod = m.Product(sku=sku, name=f"Produit {sku}", unit="kg", unit_price=95, perishable=True)
        prod.supplier = sup
        session.add_all([sup, prod])
        await session.flush()
        session.add(m.Stock(product_id=prod.id, quantity=5, reorder_threshold=10))
        if with_history:
            for d in range(40):
                day = datetime.datetime(2026, 5, 1) + datetime.timedelta(days=d)
                qty = 10 + d % 5
                session.add(
                    m.Sale(
                        product_id=prod.id, quantity=qty, unit_price=95, total=qty * 95, sold_at=day
                    )
                )
            inv = m.Invoice(number=f"FAC-{org_id}", currency="EUR", total_amount=100)
            inv.lines.append(
                m.InvoiceLine(
                    product_id=prod.id, description="x", quantity=1, unit_price=100, line_total=100
                )
            )
            session.add(inv)
        await session.flush()
    return prod


async def _init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(m.Base.metadata.create_all)
    async with TestSession() as s:
        # Deux organisations distinctes.
        org_a = m.Organization(name="Org A", slug="org-a")
        org_b = m.Organization(name="Org B", slug="org-b")
        s.add_all([org_a, org_b])

        def _user(email: str) -> m.User:
            return m.User(email=email, hashed_password=hash_password("secret"))

        admin = _user("admin@test.local")  # owner A
        viewer = _user("viewer@test.local")  # read_only A
        accountant = _user("accountant@test.local")  # accountant A
        owner_b = _user("owner@b.local")  # owner B
        s.add_all([admin, viewer, accountant, owner_b])
        await s.flush()

        s.add_all(
            [
                m.Membership(user_id=admin.id, organization_id=org_a.id, role=MembershipRole.OWNER),
                m.Membership(
                    user_id=viewer.id, organization_id=org_a.id, role=MembershipRole.READ_ONLY
                ),
                m.Membership(
                    user_id=accountant.id, organization_id=org_a.id, role=MembershipRole.ACCOUNTANT
                ),
                m.Membership(
                    user_id=owner_b.id, organization_id=org_b.id, role=MembershipRole.OWNER
                ),
            ]
        )
        await s.flush()

        # Org A : produit complet (id 1) ; Org B : produit isolé.
        await _seed_org_products(s, org_a.id, "BOEUF-HACHE", with_history=True)
        await _seed_org_products(s, org_b.id, "ORGB-ONLY", with_history=False)
        await s.commit()


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    asyncio.get_event_loop().run_until_complete(_init_db())
    yield


async def _override_db():
    async with TestSession() as s:
        yield s
        await s.commit()


@pytest.fixture
def anon_client():
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(c, email: str, password: str = "secret") -> str:
    resp = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_client(anon_client, email: str):
    token = _login(anon_client, email)
    anon_client.headers["Authorization"] = f"Bearer {token}"
    return anon_client


@pytest.fixture
def client(anon_client):
    """Owner de l'org A (défaut des tests existants)."""
    return _auth_client(anon_client, "admin@test.local")


@pytest.fixture
def viewer_client(anon_client):
    """Read-only de l'org A."""
    return _auth_client(anon_client, "viewer@test.local")


@pytest.fixture
def accountant_client(anon_client):
    """Comptable de l'org A."""
    return _auth_client(anon_client, "accountant@test.local")


@pytest.fixture
def org_b_client(anon_client):
    """Owner de l'org B (pour les tests d'isolation)."""
    return _auth_client(anon_client, "owner@b.local")
