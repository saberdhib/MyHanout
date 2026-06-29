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


def test_webhook_routes_order_intent(client):
    resp = client.post(
        "/api/v1/whatsapp/webhook",
        json={"from": "+212600000000", "message": "je veux passer une commande"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"] == "agent_order"
    # Action sensible -> validation humaine requise.
    assert data["requires_approval"] is True
