"""Tests carnet HACCP : plan de nettoyage, traçabilité, conformité température, registre."""

from __future__ import annotations

import asyncio
import datetime
import uuid
from datetime import UTC, timedelta

from sqlalchemy import select

import app.models as m
from app.core.tenancy import tenant_context
from app.models.base import EquipmentKind
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _seed_fridge(slug: str = "org-a") -> int:
    """Un frigo avec 3 relevés dont 1 hors plage (0–4 °C)."""
    async with TestSession() as s:
        org = (await s.scalars(select(m.Organization).where(m.Organization.slug == slug))).first()
        assert org is not None
        with tenant_context(org.id):
            eq = m.Equipment(
                name=f"Frigo test {uuid.uuid4().hex[:6]}",
                kind=EquipmentKind.FRIDGE,
                min_temp_c=0,
                max_temp_c=4,
            )
            s.add(eq)
            await s.flush()
            now = datetime.datetime.now(UTC)
            for hours_ago, temp in ((3, 2.5), (2, 3.0), (1, 7.2)):  # 7.2 = écart
                s.add(
                    m.TemperatureReading(
                        equipment_id=eq.id,
                        temp_c=temp,
                        recorded_at=now - timedelta(hours=hours_ago),
                        source="test",
                    )
                )
            await s.flush()  # flush DANS le tenant_context → estampille organization_id
        await s.commit()
        return eq.id


def test_default_plan_and_complete_flow(client):
    tasks = client.get("/api/v1/haccp/tasks").json()["items"]
    assert tasks, "le plan de nettoyage par défaut doit être créé au premier accès"
    daily = next(t for t in tasks if t["frequency"] == "daily")
    assert daily["due"] is True  # jamais exécutée → à faire

    # Exécution tracée (horodatée, avec l'auteur).
    r = client.post(f"/api/v1/haccp/tasks/{daily['id']}/complete", json={"note": "fait"})
    assert r.status_code == 204
    after = client.get("/api/v1/haccp/tasks").json()["items"]
    mine = next(t for t in after if t["id"] == daily["id"])
    assert mine["due"] is False
    assert mine["last_done_by"] == "admin@test.local"


def test_custom_task_crud(client):
    created = client.post(
        "/api/v1/haccp/tasks", json={"name": "Nettoyage vitrine test", "frequency": "weekly"}
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]
    assert created.json()["due"] is True
    assert client.delete(f"/api/v1/haccp/tasks/{tid}").status_code == 204


def test_register_compliance_and_breach(client):
    eq_id = _run(_seed_fridge())
    reg = client.get("/api/v1/haccp/register", params={"days": 7}).json()
    mine = next(t for t in reg["temperature"] if t["equipment_id"] == eq_id)
    assert mine["readings"] == 3
    assert mine["in_range"] == 2
    assert 0 < mine["compliance_pct"] < 100
    assert mine["breaches"], "l'écart à 7.2°C doit être listé"
    assert reg["explanation"]
    # Les exécutions d'hygiène tracées apparaissent au registre.
    tasks = client.get("/api/v1/haccp/tasks").json()["items"]
    client.post(f"/api/v1/haccp/tasks/{tasks[0]['id']}/complete", json={})
    reg2 = client.get("/api/v1/haccp/register").json()
    assert any(h["task_id"] == tasks[0]["id"] for h in reg2["hygiene"])
