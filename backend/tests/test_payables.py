"""Tests échéancier fournisseurs + trésorerie prévisionnelle (org dédiée, robuste)."""

from __future__ import annotations

import asyncio
import datetime

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.models.invoice import Invoice
from app.models.organization import Membership, MembershipRole, Organization
from app.models.product import Product
from app.models.sale import Sale
from app.models.supplier import Supplier
from app.models.user import User
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _shop_with_payables(slug: str, owner_email: str) -> tuple[int, int]:
    """Org dédiée + owner + factures (1 en retard, 1 sous 7j, 1 payée) + ventes."""
    today = datetime.date.today()
    async with TestSession() as s:
        org = Organization(name=slug, slug=slug)
        s.add(org)
        await s.flush()
        u = User(email=owner_email, hashed_password=hash_password("secret"))
        s.add(u)
        await s.flush()
        s.add(Membership(user_id=u.id, organization_id=org.id, role=MembershipRole.OWNER))
        with tenant_context(org.id):
            sup = Supplier(name="Fournisseur Payables", payment_terms_days=30)
            prod = Product(sku=f"{slug}-P", name="P", unit="kg", unit_price=20)
            s.add_all([sup, prod])
            await s.flush()
            overdue = Invoice(
                number="OVERDUE",
                supplier_id=sup.id,
                due_date=today - datetime.timedelta(days=3),
                total_amount=100,
                paid=False,
            )
            soon = Invoice(
                number="SOON",
                supplier_id=sup.id,
                due_date=today + datetime.timedelta(days=3),
                total_amount=50,
                paid=False,
            )
            done = Invoice(number="PAID", total_amount=200, paid=True)
            s.add_all([overdue, soon, done])
            # Ventes récentes (entrées estimées).
            for d in range(30):
                s.add(
                    Sale(
                        product_id=prod.id,
                        quantity=1,
                        unit_price=20,
                        total=20,
                        sold_at=datetime.datetime.now() - datetime.timedelta(days=d),
                    )
                )
            await s.flush()
            overdue_id = overdue.id
        await s.commit()
    return org.id, overdue_id


def _login(anon_client, email: str) -> dict:
    r = anon_client.post("/api/v1/auth/login", json={"email": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_payables_buckets_and_projection(anon_client):
    _run(_shop_with_payables("pay-1", "pay1@test.local"))
    h = _login(anon_client, "pay1@test.local")
    v = anon_client.get("/api/v1/finance/payables", headers=h).json()

    assert v["total_due"] == 150.0  # 100 + 50 (payée exclue)
    assert v["overdue_amount"] == 100.0
    keys = {b["key"]: b["amount"] for b in v["buckets"]}
    assert keys.get("overdue") == 100.0
    assert keys.get("d7") == 50.0
    # Projection : 4 semaines, chaque semaine porte une entrée estimée.
    assert len(v["weeks"]) == 4
    assert all("running_balance" in w for w in v["weeks"])
    # Les retards pèsent sur la 1re semaine (payables_due >= 100).
    assert v["weeks"][0]["payables_due"] >= 100.0


def test_mark_paid_updates_schedule(anon_client):
    _, overdue_id = _run(_shop_with_payables("pay-2", "pay2@test.local"))
    h = _login(anon_client, "pay2@test.local")
    assert anon_client.get("/api/v1/finance/payables", headers=h).json()["total_due"] == 150.0

    paid = anon_client.post(f"/api/v1/finance/invoices/{overdue_id}/pay", headers=h)
    assert paid.status_code == 200, paid.text
    # L'échéancier ne compte plus la facture réglée.
    after = anon_client.get("/api/v1/finance/payables", headers=h).json()
    assert after["total_due"] == 50.0
    assert after["overdue_amount"] == 0.0


def test_payables_requires_finance_scope(anon_client):
    # Un read_only n'a pas le scope finance.
    h = _login(anon_client, "viewer@test.local")
    assert anon_client.get("/api/v1/finance/payables", headers=h).status_code == 403
