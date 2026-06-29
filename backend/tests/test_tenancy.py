"""Tests d'isolation multi-tenant (le plus important) + matrice de rôles.

L'isolation est une exigence de SÉCURITÉ : org A ne doit JAMAIS accéder à org B.
"""

import pytest
from sqlalchemy import select

from app.core.tenancy import tenant_context
from app.models.organization import Organization
from app.models.product import Product
from tests.conftest import TestSession

# --- Isolation API ----------------------------------------------------------


def test_org_a_sees_only_its_stock(client):
    skus = {s["product_sku"] for s in client.get("/api/v1/stocks").json()["items"]}
    assert "BOEUF-HACHE" in skus
    assert "ORGB-ONLY" not in skus  # produit de l'org B invisible


def test_org_b_sees_only_its_stock(org_b_client):
    skus = {s["product_sku"] for s in org_b_client.get("/api/v1/stocks").json()["items"]}
    assert "ORGB-ONLY" in skus
    assert "BOEUF-HACHE" not in skus  # produit de l'org A invisible


# --- Isolation au niveau du garde-fou central (ORM) -------------------------


@pytest.mark.asyncio
async def test_guard_blocks_cross_tenant_get():
    """Même en connaissant l'id, une autre org ne peut PAS lire la ligne."""
    async with TestSession() as s:
        # Sans contexte tenant : pas de filtre -> on récupère les ids réels.
        prod_a = await s.scalar(select(Product).where(Product.sku == "BOEUF-HACHE"))
        org_b = await s.scalar(select(Organization).where(Organization.slug == "org-b"))
        assert prod_a is not None and org_b is not None
        a_id = prod_a.id

    async with TestSession() as s:
        with tenant_context(org_b.id):
            # session.get filtré : l'org B ne voit pas le produit de l'org A.
            assert await s.get(Product, a_id) is None
            # ...mais voit bien le sien.
            own = await s.scalar(select(Product).where(Product.sku == "ORGB-ONLY"))
            assert own is not None


@pytest.mark.asyncio
async def test_guard_stamps_org_on_insert():
    """Un INSERT sans organization_id explicite est estampillé par le contexte."""
    async with TestSession() as s:
        org_b = await s.scalar(select(Organization).where(Organization.slug == "org-b"))
        with tenant_context(org_b.id):
            p = Product(sku="STAMP-TEST", name="Stamp", unit="kg")
            s.add(p)
            await s.flush()
            assert p.organization_id == org_b.id
        await s.rollback()


# --- Matrice de rôles -------------------------------------------------------


def test_accountant_cannot_send_orders(accountant_client):
    # Le comptable lit les factures mais n'a pas le scope "orders".
    assert accountant_client.get("/api/v1/invoices").status_code == 200
    assert accountant_client.post("/api/v1/orders/1/approve").status_code == 403


def test_owner_has_orders_scope(client):
    # Owner (scope *) passe le contrôle de permission (404 car commande absente).
    assert client.post("/api/v1/orders/1/approve").status_code != 403
