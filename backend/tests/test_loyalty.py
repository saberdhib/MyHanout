"""Tests fidélité client (gain/échange de points, explicabilité, isolation)."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.tenancy import tenant_context
from app.models.customer import Customer
from app.models.organization import Organization
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _new_customer(slug: str, name: str) -> int:
    async with TestSession() as s:
        org = await s.scalar(select(Organization).where(Organization.slug == slug))
        assert org is not None
        with tenant_context(org.id):
            c = Customer(name=name, consent_opt_in=True)
            s.add(c)
            await s.flush()
            cid = c.id
            await s.commit()
    return cid


def test_earn_and_reward_status(client):
    cid = _run(_new_customer("org-a", "Fidèle A"))

    r = client.post(f"/api/v1/loyalty/{cid}/earn", json={"amount": 30})
    assert r.status_code == 200, r.text
    assert r.json()["points_balance"] == 30  # 1 pt / €
    assert r.json()["reward_ready"] is False
    assert r.json()["points_to_next"] == 70

    client.post(f"/api/v1/loyalty/{cid}/earn", json={"amount": 30})
    body = client.post(f"/api/v1/loyalty/{cid}/earn", json={"amount": 50}).json()
    assert body["points_balance"] == 110
    assert body["reward_ready"] is True
    assert body["rewards_available"] == 1


def test_redeem_requires_threshold(client):
    cid = _run(_new_customer("org-a", "Petit solde"))
    client.post(f"/api/v1/loyalty/{cid}/earn", json={"amount": 20})
    # Solde 20 < seuil 100 -> refus.
    assert client.post(f"/api/v1/loyalty/{cid}/redeem").status_code == 400


def test_redeem_debits_points_and_logs(client):
    cid = _run(_new_customer("org-a", "Récompense"))
    client.post(f"/api/v1/loyalty/{cid}/earn", json={"amount": 120})
    red = client.post(f"/api/v1/loyalty/{cid}/redeem")
    assert red.status_code == 200, red.text
    assert red.json()["points_spent"] == 100
    assert red.json()["points_balance"] == 20

    # Le grand livre trace gain + échange.
    detail = client.get(f"/api/v1/loyalty/{cid}").json()
    kinds = [t["kind"] for t in detail["transactions"]]
    assert "earn" in kinds and "redeem" in kinds


def test_loyalty_tenant_isolation(client, org_b_client):
    cid = _run(_new_customer("org-a", "Client A only"))
    client.post(f"/api/v1/loyalty/{cid}/earn", json={"amount": 40})
    # L'org B ne voit pas le compte fidélité d'un client de l'org A.
    assert org_b_client.get(f"/api/v1/loyalty/{cid}").status_code == 404
    ids = {a["customer_id"] for a in org_b_client.get("/api/v1/loyalty").json()["items"]}
    assert cid not in ids


def test_accountant_cannot_earn(accountant_client):
    # Le comptable n'a pas le scope "orders" (action commerciale).
    assert accountant_client.post("/api/v1/loyalty/1/earn", json={"amount": 10}).status_code == 403
