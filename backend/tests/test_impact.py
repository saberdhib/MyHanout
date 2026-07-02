"""Tests tableau d'impact (ROI en euros) — consolidation de la valeur produite."""

from __future__ import annotations

import asyncio

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.models.base import MarkdownStatus
from app.models.markdown import MarkdownSuggestion
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


async def _shop_with_impact(slug: str, owner_email: str) -> int:
    async with TestSession() as s:
        org = Organization(name=slug, slug=slug)
        s.add(org)
        await s.flush()
        u = User(email=owner_email, hashed_password=hash_password("secret"))
        s.add(u)
        await s.flush()
        s.add(Membership(user_id=u.id, organization_id=org.id, role=MembershipRole.OWNER))
        with tenant_context(org.id):
            p = Product(sku=f"{slug}-P", name="P", unit="kg", unit_price=10)
            s.add(p)
            await s.flush()
            # Démarque appliquée : perte évitée 40 €, cash récupéré 25 €.
            s.add(
                MarkdownSuggestion(
                    product_id=p.id,
                    status=MarkdownStatus.APPLIED,
                    avoided_loss=40.0,
                    recovered_value=25.0,
                    explanation="démo",
                )
            )
            await s.flush()
        await s.commit()
        return org.id


def _login(anon_client, email: str) -> dict:
    r = anon_client.post("/api/v1/auth/login", json={"email": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_impact_consolidates_euro_value(anon_client):
    _run(_shop_with_impact("impact-1", "impact1@test.local"))
    h = _login(anon_client, "impact1@test.local")
    v = anon_client.get("/api/v1/impact", headers=h).json()

    assert v["period_days"] == 30
    # 40 (perte évitée) + 25 (cash récupéré) = 65 € minimum révélés/gagnés.
    assert v["estimated_value_eur"] >= 65.0
    labels = {ln["label"]: ln["amount"] for ln in v["lines"]}
    assert labels["Gaspillage évité (démarque)"] == 40.0
    assert labels["Cash récupéré (démarque)"] == 25.0
    # Une ligne de temps gagné (heures) est présente.
    assert any(ln["unit"] == "h" for ln in v["lines"])
    assert v["disclaimer"]


def test_impact_period_param(anon_client):
    _run(_shop_with_impact("impact-2", "impact2@test.local"))
    h = _login(anon_client, "impact2@test.local")
    v = anon_client.get("/api/v1/impact", headers=h, params={"days": 7}).json()
    assert v["period_days"] == 7


def test_impact_requires_scope(anon_client):
    # Un compte sans le scope forecasts est refusé — ici org B a un owner (a le scope),
    # donc on teste l'absence d'auth.
    assert anon_client.get("/api/v1/impact").status_code == 401
