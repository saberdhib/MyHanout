"""Tests demo pack : chat web, signaux, clients (RGPD), promo flash + publication."""

import datetime

import pytest
from sqlalchemy import select

from app.core.tenancy import tenant_context
from app.models.organization import Organization
from app.models.stock import Stock
from tests.conftest import TestSession


def test_signals_endpoint(client):
    resp = client.get("/api/v1/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert "temp_c" in data["weather"]
    assert len(data["trends"]) >= 1


def test_web_chat(client):
    resp = client.post("/api/v1/chat", json={"message": "bonjour, une question"})
    assert resp.status_code == 200
    assert resp.json()["reply"]
    assert resp.json()["agent"]


def test_customer_consent_recorded(client):
    resp = client.post(
        "/api/v1/customers",
        json={"name": "Client A", "phone": "+212611111111", "consent_opt_in": True},
    )
    assert resp.status_code == 201
    assert resp.json()["consent_opt_in"] is True


@pytest.mark.asyncio
async def _seed_expiring_and_customers():
    """Crée un stock proche péremption (org A) + 1 client opt-in + 1 non opt-in."""
    from app.models.customer import Customer

    async with TestSession() as s:
        org_a = await s.scalar(select(Organization).where(Organization.slug == "org-a"))
        with tenant_context(org_a.id):
            soon = datetime.date.today() + datetime.timedelta(days=2)
            s.add(Stock(product_id=1, quantity=4, reorder_threshold=10, expiry_date=soon))
            s.add(Customer(name="Opt-in", phone="+212600000001", consent_opt_in=True))
            s.add(Customer(name="No-consent", phone="+212600000002", consent_opt_in=False))
            await s.commit()  # commit DANS le contexte -> estampillage tenant


def _run(coro):
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_flash_promo_scan_publish_rgpd(client):
    _run(_seed_expiring_and_customers())

    # Scan : détecte le produit en fin de vie -> promo en brouillon (explicable).
    scan = client.post("/api/v1/promos/scan", params={"within_days": 3})
    assert scan.status_code == 200
    items = scan.json()["items"]
    assert items, "une promo flash doit être proposée pour le produit en fin de vie"
    promo = items[0]
    assert promo["status"] == "draft"
    assert "périme" in (promo["reason"] or "")

    pub = client.post(
        f"/api/v1/promos/{promo['id']}/publish",
        json={"channels": ["social", "customers"]},
    )
    assert pub.status_code == 200
    data = pub.json()
    assert data["status"] == "published"
    assert data["audience_count"] >= 1  # diffusé aux clients opt-in


@pytest.mark.asyncio
async def test_customer_broadcast_excludes_non_consenting():
    """RGPD déterministe : seuls les clients opt-in reçoivent (org B, isolée)."""
    from app.messaging.publish import CustomerBroadcastChannel
    from app.models.customer import Customer

    async with TestSession() as s:
        org_b = await s.scalar(select(Organization).where(Organization.slug == "org-b"))
        with tenant_context(org_b.id):
            s.add(Customer(name="oui", phone="+212699990001", consent_opt_in=True))
            s.add(Customer(name="non", phone="+212699990002", consent_opt_in=False))
            await s.flush()
            result = await CustomerBroadcastChannel().publish(
                s, organization_id=org_b.id, message="promo"
            )
            assert result.delivered == 1  # le non-consentant est exclu
        await s.rollback()


def test_marketing_scope_required(viewer_client):
    # read_only n'a pas le scope "marketing".
    assert viewer_client.post("/api/v1/promos/scan").status_code == 403
