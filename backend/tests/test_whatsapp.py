"""Tests webhook WhatsApp : handshake, signature, routage texte/image, état."""


def test_webhook_verify_ok(client):
    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "local-verify-token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_verify_forbidden(client):
    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
    )
    assert resp.status_code == 403


def test_webhook_text_fallback(anon_client):
    # Webhook public (pas d'auth). Message générique -> fallback orchestrateur.
    resp = anon_client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": "+212600000000", "message": "bonjour"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] == 1
    assert data["replies"][0]["reply"]


def test_webhook_order_conversation_flow(anon_client):
    phone = "+212600000111"
    # 1) Demande de commande -> proposition + état awaiting.
    r1 = anon_client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": phone, "message": "commande pour demain"},
    ).json()
    assert "Proposition de commande" in r1["replies"][0]["reply"]
    # 2) Validation -> commande confirmée.
    r2 = anon_client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": phone, "message": "oui"},
    ).json()
    assert "confirmée" in r2["replies"][0]["reply"]


def test_webhook_stock_entry_via_whatsapp(anon_client):
    resp = anon_client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": "+212600000222", "message": "stock BOEUF-HACHE 3 12"},
    ).json()
    assert "Saisie enregistrée" in resp["replies"][0]["reply"]


def test_webhook_image_routes_to_ocr(anon_client):
    resp = anon_client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": "+212600000333", "image_id": "MEDIA-1"},
    ).json()
    # L'image est téléchargée (mock) puis passée au pipeline OCR -> facture en revue.
    assert "Facture reçue" in resp["replies"][0]["reply"]


def test_webhook_bad_signature_rejected(anon_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "whatsapp_app_secret", "topsecret")
    resp = anon_client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": "+212600000444", "message": "bonjour"},
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert resp.status_code == 403
