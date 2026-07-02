"""Tests backtest de prévision : mesure honnête MAE/MAPE par modèle + verdict."""

from __future__ import annotations

import asyncio
import datetime

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.models.organization import Membership, MembershipRole, Organization
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User
from tests.conftest import TestSession

# Ventes plus fortes le week-end (saisonnalité hebdo) → le naïf doit battre la moyenne plate.
_WEEKDAY_QTY = {0: 8, 1: 8, 2: 9, 3: 9, 4: 11, 5: 14, 6: 6}


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _shop_with_history(slug: str, owner_email: str, days: int = 70) -> int:
    async with TestSession() as s:
        org = Organization(name=slug, slug=slug)
        s.add(org)
        await s.flush()
        u = User(email=owner_email, hashed_password=hash_password("secret"))
        s.add(u)
        await s.flush()
        s.add(Membership(user_id=u.id, organization_id=org.id, role=MembershipRole.OWNER))
        with tenant_context(org.id):
            p = Product(sku=f"{slug}-P", name="Saisonnier", unit="kg", unit_price=10)
            s.add(p)
            await s.flush()
            base = datetime.datetime(2026, 1, 1)
            for d in range(days):
                day = base + datetime.timedelta(days=d)
                qty = _WEEKDAY_QTY[day.weekday()]
                s.add(
                    Sale(product_id=p.id, quantity=qty, unit_price=10, total=qty * 10, sold_at=day)
                )
            pid = p.id
            await s.commit()
        return pid


def _login(anon_client, email: str) -> dict:
    r = anon_client.post("/api/v1/auth/login", json={"email": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_backtest_reports_metrics_and_availability(anon_client):
    pid = _run(_shop_with_history("bt-1", "bt1@test.local"))
    h = _login(anon_client, "bt1@test.local")
    v = anon_client.get(f"/api/v1/forecasts/{pid}/backtest", headers=h).json()

    by_model = {r["model"]: r for r in v["results"]}
    # Baseline + naïf évalués (MAPE calculée) ; prophet/lgbm signalés indisponibles.
    assert by_model["mean"]["available"] and by_model["mean"]["mape"] is not None
    assert by_model["naive"]["available"] and by_model["naive"]["mape"] is not None
    assert by_model["prophet"]["available"] is False
    assert by_model["lgbm"]["available"] is False
    assert v["best_model"] in {"mean", "naive"}
    assert v["verdict"]


def test_backtest_insufficient_history(anon_client):
    pid = _run(_shop_with_history("bt-2", "bt2@test.local", days=20))
    h = _login(anon_client, "bt2@test.local")
    v = anon_client.get(f"/api/v1/forecasts/{pid}/backtest", headers=h).json()
    assert "insuffisant" in v["verdict"].lower()
    assert v["best_model"] is None
