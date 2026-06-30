"""Tests du socle data platform : pipelines, reco, alertes, SSE, isolation tenant."""

from __future__ import annotations

import asyncio

from app.intelligence.recommendation.engine import decide
from tests.conftest import _login


# --- Moteur de reco : règles pures, explicables -----------------------------
def test_decide_order_when_stockout_risk():
    d = decide(
        product_id=1,
        forecast_demand=100,
        current_stock=10,
        reorder_threshold=20,
        horizon_days=14,
        history_days=40,
    )
    assert d.action == "order"
    assert d.suggested_quantity > 0
    assert d.risk_factor > 0.5
    assert d.explanation and d.reasons  # explicabilité


def test_decide_hold_when_stock_sufficient():
    d = decide(
        product_id=1,
        forecast_demand=10,
        current_stock=50,
        reorder_threshold=5,
        horizon_days=14,
        history_days=40,
    )
    assert d.action in ("hold", "reduce")


def test_decide_fallback_short_history():
    d = decide(
        product_id=1,
        forecast_demand=100,
        current_stock=0,
        reorder_threshold=10,
        horizon_days=7,
        history_days=3,
    )
    assert d.confidence <= 0.5  # confiance pénalisée
    assert "insuffisant" in " ".join(d.reasons)


def test_decide_perishable_caps_quantity():
    short = decide(
        product_id=1,
        forecast_demand=200,
        current_stock=0,
        reorder_threshold=10,
        horizon_days=30,
        history_days=60,
        perishable=True,
        shelf_life_days=3,
    )
    long = decide(
        product_id=1,
        forecast_demand=200,
        current_stock=0,
        reorder_threshold=10,
        horizon_days=30,
        history_days=60,
        perishable=False,
    )
    assert short.suggested_quantity <= long.suggested_quantity


# --- Pipeline bout-en-bout (via API) ----------------------------------------
def test_pipeline_trigger_and_traceability(client):
    r = client.post("/api/v1/pipelines/daily/trigger")
    assert r.status_code == 200, r.text
    run = r.json()
    assert run["status"] == "success"
    assert run["rows_processed"] >= 1
    run_id = run["id"]

    runs = client.get("/api/v1/pipelines/runs").json()
    assert any(x["id"] == run_id for x in runs["items"])

    # Les recommandations référencent le run qui les a produites (traçabilité).
    recs = client.get("/api/v1/recommendations").json()
    assert recs["total"] >= 1
    assert any(x["pipeline_run_id"] for x in recs["items"])
    assert all(x["explanation"] for x in recs["items"])  # explicabilité


def test_pipeline_health(client):
    client.post("/api/v1/pipelines/daily/trigger")
    h = client.get("/api/v1/pipelines/health").json()
    jobs = {j["job_name"]: j for j in h["jobs"]}
    assert "daily" in jobs


def test_unknown_job_404(client):
    assert client.post("/api/v1/pipelines/does-not-exist/trigger").status_code == 404


def test_forecasts_recompute(client):
    r = client.post("/api/v1/forecasts/recompute")
    assert r.status_code == 200, r.text
    assert r.json()["job_name"] == "recommend"


# --- Simulation de commande --------------------------------------------------
def test_simulate_order(client):
    r = client.post("/api/v1/recommendations/simulate", json={"product_id": 1, "quantity": 50})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ordered_quantity"] == 50
    assert "projected_stock" in body and body["explanation"]


# --- Alertes : génération + résolution humaine -------------------------------
def test_alerts_generated_and_resolved(client):
    client.post("/api/v1/pipelines/daily/trigger")
    alerts = client.get("/api/v1/alerts").json()
    assert alerts["total"] >= 1
    alert_id = alerts["items"][0]["id"]

    res = client.post(f"/api/v1/alerts/{alert_id}/resolve", json={"note": "réassort lancé"})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "resolved"


def test_alert_resolve_requires_orders_permission(anon_client):
    # read_only n'a pas le scope "orders" → ne peut pas résoudre.
    token = _login(anon_client, "viewer@test.local")
    anon_client.headers["Authorization"] = f"Bearer {token}"
    # crée une alerte d'abord (owner)
    owner = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {owner}"
    anon_client.post("/api/v1/pipelines/scan_alerts/trigger")
    a = anon_client.get("/api/v1/alerts").json()
    if a["total"] == 0:
        return
    aid = a["items"][0]["id"]
    viewer = _login(anon_client, "viewer@test.local")
    anon_client.headers["Authorization"] = f"Bearer {viewer}"
    assert anon_client.post(f"/api/v1/alerts/{aid}/resolve", json={}).status_code == 403


# --- Isolation multi-tenant sur les nouvelles entités ------------------------
def test_pipeline_runs_isolated_between_tenants(anon_client):
    a_token = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {a_token}"
    anon_client.post("/api/v1/pipelines/daily/trigger")
    a_runs = anon_client.get("/api/v1/pipelines/runs").json()
    a_ids = {x["id"] for x in a_runs["items"]}
    assert a_ids  # A a des runs

    b_token = _login(anon_client, "owner@b.local")
    anon_client.headers["Authorization"] = f"Bearer {b_token}"
    b_runs = anon_client.get("/api/v1/pipelines/runs").json()
    b_ids = {x["id"] for x in b_runs["items"]}
    # B ne voit AUCUN run de A.
    assert a_ids.isdisjoint(b_ids)


# --- SSE : bus filtré par tenant --------------------------------------------
def test_event_broker_is_tenant_scoped():
    from app.core.events import StreamEvent, broker

    async def run():
        qa = broker.subscribe(101)
        qb = broker.subscribe(202)
        broker.publish(101, StreamEvent(type="alert_created", payload={"id": 1}))
        await asyncio.sleep(0)
        assert qa.qsize() == 1  # l'org 101 reçoit
        assert qb.qsize() == 0  # l'org 202 ne reçoit rien
        broker.unsubscribe(101, qa)
        broker.unsubscribe(202, qb)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()
