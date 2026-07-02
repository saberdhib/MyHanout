"""Idempotence des webhooks entrants (Lot 6) — WhatsApp & Slack.

Un fournisseur re-livre parfois le même event (retry). On ne doit le traiter qu'une fois.
"""

from __future__ import annotations


def test_whatsapp_dedup_same_message(anon_client):
    payload = {"from": "+212600000999", "message": "bonjour", "id": "wamid.IDEMP1"}
    r1 = anon_client.post("/api/v1/whatsapp/webhook", json=payload).json()
    assert r1["received"] == 1
    assert r1["skipped_duplicates"] == 0
    assert len(r1["replies"]) == 1

    # Re-livraison du même id -> ignoré (aucune 2ᵉ réponse).
    r2 = anon_client.post("/api/v1/whatsapp/webhook", json=payload).json()
    assert r2["skipped_duplicates"] == 1
    assert r2["replies"] == []


def test_whatsapp_without_id_is_always_processed(anon_client):
    # Sans id (impossible de dédupliquer) : traité à chaque fois.
    payload = {"from": "+212600000998", "message": "bonjour"}
    r1 = anon_client.post("/api/v1/whatsapp/webhook", json=payload).json()
    r2 = anon_client.post("/api/v1/whatsapp/webhook", json=payload).json()
    assert r1["skipped_duplicates"] == 0
    assert r2["skipped_duplicates"] == 0


def test_slack_dedup_same_event(anon_client):
    payload = {
        "type": "event_callback",
        "event_id": "Ev-IDEMP-1",
        "event": {"type": "message", "channel": "C123", "text": "bonjour"},
    }
    r1 = anon_client.post("/api/v1/slack/webhook", json=payload).json()
    assert r1.get("reply")
    r2 = anon_client.post("/api/v1/slack/webhook", json=payload).json()
    assert r2.get("skipped") == "duplicate"
