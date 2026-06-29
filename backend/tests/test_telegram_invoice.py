"""Tests Telegram webhook (mock) + édition/paiement de facture."""


def test_telegram_webhook_text(anon_client):
    resp = anon_client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 4242}, "text": "bonjour"}},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["reply"]


def test_telegram_webhook_photo_routes_to_ocr(anon_client):
    resp = anon_client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"chat": {"id": 4243}, "photo": [{"file_id": "F1"}]}},
    )
    assert resp.status_code == 200
    assert "Facture reçue" in resp.json()["reply"]


def test_telegram_webhook_skips_empty(anon_client):
    resp = anon_client.post("/api/v1/telegram/webhook", json={})
    assert resp.status_code == 200
    assert resp.json().get("skipped") is True


def test_invoice_patch_and_mark_paid(client):
    invoices = client.get("/api/v1/invoices").json()["items"]
    assert invoices, "une facture seedée doit exister"
    inv_id = invoices[0]["id"]

    resp = client.patch(f"/api/v1/invoices/{inv_id}", json={"number": "FAC-EDIT", "paid": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["number"] == "FAC-EDIT"
    assert data["paid"] is True
    assert data["status"] == "paid"

    # Re-bascule en non payé.
    resp2 = client.patch(f"/api/v1/invoices/{inv_id}", json={"paid": False})
    assert resp2.json()["paid"] is False
