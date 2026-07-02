"""Tests réservations client (click & collect) : cycle, fidélité au retrait, isolation.

Les parcours d'envoi/collecte tournent dans une **org dédiée** (produit + client connus,
aucun connecteur configuré → résolveur mock) pour être robustes à l'état sqlite partagé
(un connecteur WhatsApp configuré ailleurs, ou un prix produit modifié par un autre test).
"""

from __future__ import annotations

import asyncio

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.models.customer import Customer
from app.models.organization import Membership, MembershipRole, Organization
from app.models.product import Product
from app.models.user import User
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _new_shop(slug: str, owner_email: str, *, price: float = 10.0) -> tuple[int, int, int]:
    """Org dédiée + owner + 1 produit + 1 client connu. Retourne (org, product, customer)."""
    async with TestSession() as s:
        org = Organization(name=slug, slug=slug)
        s.add(org)
        await s.flush()
        u = User(email=owner_email, hashed_password=hash_password("secret"))
        s.add(u)
        await s.flush()
        s.add(Membership(user_id=u.id, organization_id=org.id, role=MembershipRole.OWNER))
        with tenant_context(org.id):
            p = Product(sku=f"{slug}-P", name="Produit test", unit="kg", unit_price=price)
            c = Customer(name="Client", phone="+2120000000", consent_opt_in=True)
            s.add_all([p, c])
            await s.flush()
            pid, cid = p.id, c.id
        await s.commit()
    return org.id, pid, cid


def _login(anon_client, email: str) -> dict:
    r = anon_client.post("/api/v1/auth/login", json={"email": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_computes_total_from_catalog(anon_client):
    _, pid, _ = _run(_new_shop("resa-create", "resa-create@test.local", price=95.0))
    h = _login(anon_client, "resa-create@test.local")
    r = anon_client.post(
        "/api/v1/reservations",
        headers=h,
        json={"customer_name": "Passage", "lines": [{"product_id": pid, "quantity": 2}]},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["total_amount"] == 190.0  # 2 × 95
    assert body["lines"][0]["product_name"] == "Produit test"


def test_status_flow_and_loyalty_on_collect(anon_client):
    _, pid, cid = _run(_new_shop("resa-flow", "resa-flow@test.local", price=95.0))
    h = _login(anon_client, "resa-flow@test.local")
    res = anon_client.post(
        "/api/v1/reservations",
        headers=h,
        json={"customer_id": cid, "lines": [{"product_id": pid, "quantity": 2}]},
    ).json()
    rid = res["id"]

    for st in ("confirmed", "ready", "collected"):
        r = anon_client.post(f"/api/v1/reservations/{rid}/status", headers=h, json={"status": st})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == st

    # Récupérée → clôturée (toute transition refusée) + points crédités (2×95 = 190).
    assert (
        anon_client.post(
            f"/api/v1/reservations/{rid}/status", headers=h, json={"status": "ready"}
        ).status_code
        == 400
    )
    acc = anon_client.get(f"/api/v1/loyalty/{cid}", headers=h).json()
    assert acc["points_balance"] == 190


def test_closed_reservation_rejects_change(anon_client):
    _, pid, _ = _run(_new_shop("resa-closed", "resa-closed@test.local"))
    h = _login(anon_client, "resa-closed@test.local")
    rid = anon_client.post(
        "/api/v1/reservations",
        headers=h,
        json={"customer_name": "X", "lines": [{"product_id": pid, "quantity": 1}]},
    ).json()["id"]
    anon_client.post(f"/api/v1/reservations/{rid}/status", headers=h, json={"status": "cancelled"})
    assert (
        anon_client.post(
            f"/api/v1/reservations/{rid}/status", headers=h, json={"status": "ready"}
        ).status_code
        == 400
    )


def test_reservation_isolation(anon_client):
    _, pid, _ = _run(_new_shop("resa-iso", "resa-iso@test.local"))
    ha = _login(anon_client, "resa-iso@test.local")
    hb = _login(anon_client, "owner@b.local")  # org B (autre commerce)
    rid = anon_client.post(
        "/api/v1/reservations",
        headers=ha,
        json={"customer_name": "A only", "lines": [{"product_id": pid, "quantity": 1}]},
    ).json()["id"]
    assert anon_client.get(f"/api/v1/reservations/{rid}", headers=hb).status_code == 404


def test_accountant_cannot_create(accountant_client):
    payload = {"customer_name": "X", "lines": [{"product_id": 1, "quantity": 1}]}
    assert accountant_client.post("/api/v1/reservations", json=payload).status_code == 403
