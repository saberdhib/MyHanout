"""Omni-accès : capteurs température (chaîne du froid), connecteur caisse, isolation."""

import asyncio

from app.ingestion.sensors import get_sensor_provider


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Capteurs (mock keyless déterministe) ----------------------------------
def test_sensor_mock_deterministic_and_drift():
    p = get_sensor_provider()
    a = _run(p.read("sensor-fridge-1", kind="fridge"))
    b = _run(p.read("sensor-fridge-1", kind="fridge"))
    assert a.temp_c == b.temp_c  # déterministe
    hot = _run(p.read("sensor-fridge-hot", kind="fridge"))
    assert hot.temp_c > 4  # dérive simulée → hors plage frigo


def _make_equipment(org_id: int, sensor_id: str, *, name: str = "Frigo test", mn=0, mx=4) -> int:
    from app.core.tenancy import tenant_context
    from app.models.base import EquipmentKind
    from app.models.equipment import Equipment

    from .conftest import TestSession

    async def _do() -> int:
        async with TestSession() as s:
            with tenant_context(org_id):
                eq = Equipment(
                    name=name,
                    kind=EquipmentKind.FRIDGE,
                    min_temp_c=mn,
                    max_temp_c=mx,
                    sensor_external_id=sensor_id,
                )
                s.add(eq)
                await s.flush()
                eid = eq.id
                await s.commit()
            return eid

    return _run(_do())


def test_equipment_poll_and_status(client):
    _make_equipment(1, "sensor-fridge-hot")  # org A, capteur en dérive
    poll = client.post("/api/v1/equipment/poll")
    assert poll.status_code == 200, poll.text
    assert poll.json()["readings"] >= 1

    status = client.get("/api/v1/equipment").json()
    assert status["items"], "au moins un équipement"
    hot = next((i for i in status["items"] if i["status"] == "alert"), None)
    assert hot is not None
    assert hot["explanation"]  # explicable


def test_equipment_create(client):
    r = client.post(
        "/api/v1/equipment",
        json={"name": "Congel test", "kind": "freezer", "min_temp_c": -25, "max_temp_c": -18},
    )
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "freezer"


# --- Connecteur caisse (idempotent) ----------------------------------------
def test_pos_sync_is_idempotent(client):
    r1 = client.post("/api/v1/import/pos/sync")
    assert r1.status_code == 200, r1.text
    first = r1.json()
    assert first["provider"] == "mock"
    # Au moins une vente insérée (SKU connus : BAGUETTE/LAIT/POULET selon seed).
    r2 = client.post("/api/v1/import/pos/sync")
    second = r2.json()
    # Le 2e passage ne réinsère rien (idempotence par external_ref).
    assert second["inserted"] == 0
    assert second["duplicates"] >= first["inserted"]


# --- Isolation multi-tenant sur les équipements ----------------------------
def test_equipment_isolation(anon_client):
    # NB : les fixtures client/org_b_client partagent le même TestClient ; on
    # contrôle donc le token explicitement pour comparer les deux vues.
    from .conftest import _login

    iso = "Frigo ISO-A"
    _make_equipment(1, "sensor-iso-a", name=iso)  # org A (id 1)

    anon_client.headers["Authorization"] = f"Bearer {_login(anon_client, 'owner@b.local')}"
    b_names = {i["name"] for i in anon_client.get("/api/v1/equipment").json()["items"]}
    assert iso not in b_names  # B ne voit jamais l'équipement d'A

    anon_client.headers["Authorization"] = f"Bearer {_login(anon_client, 'admin@test.local')}"
    a_names = {i["name"] for i in anon_client.get("/api/v1/equipment").json()["items"]}
    assert iso in a_names  # A le voit bien


def test_equipment_requires_permission(anon_client):
    assert anon_client.get("/api/v1/equipment").status_code in (401, 403)
