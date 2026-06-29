"""Tests suggestion de commande explicable + validation 3 modes."""


def test_suggest_returns_explained_lines(client):
    resp = client.post("/api/v1/orders/suggest", json={"horizon": "demain"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["horizon_days"] == 1
    assert data["lines"], "au moins une suggestion attendue (seed BOEUF-HACHE)"
    line = data["lines"][0]
    # Explicabilité obligatoire.
    assert line["explanation"]
    assert "predicted_demand" in line
    assert "current_stock" in line
    assert 0.0 <= line["confidence"] <= 1.0


def test_suggest_horizon_keyword_week(client):
    resp = client.post("/api/v1/orders/suggest", json={"horizon": "semaine"})
    assert resp.json()["horizon_days"] == 7


def test_confirm_record_only_creates_confirmed_order(client):
    resp = client.post(
        "/api/v1/orders/confirm",
        json={"lines": [{"product_id": 1, "quantity": 10}], "action_mode": "record_only"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["action_mode"] == "record_only"
    assert len(data["lines"]) == 1
    # Brouillon/message toujours généré (utile même en record_only).
    assert data["supplier_message"]


def test_confirm_draft_mode_does_not_send(client):
    resp = client.post(
        "/api/v1/orders/confirm",
        json={"lines": [{"product_id": 1, "quantity": 5}], "action_mode": "draft"},
    )
    data = resp.json()
    # draft : rien envoyé -> statut reste confirmed (pas "sent").
    assert data["status"] == "confirmed"
    assert data["supplier_message"].startswith("Bonjour")
