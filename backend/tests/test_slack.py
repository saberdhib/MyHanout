"""Tests connecteur Slack : challenge d'activation + event message + anti-boucle."""

from __future__ import annotations


def test_slack_url_verification(anon_client):
    r = anon_client.post(
        "/api/v1/slack/webhook",
        json={"type": "url_verification", "challenge": "abc123"},
    )
    assert r.status_code == 200
    assert r.json()["challenge"] == "abc123"


def test_slack_message_event_gets_reply(anon_client):
    r = anon_client.post(
        "/api/v1/slack/webhook",
        json={
            "type": "event_callback",
            "event": {"type": "message", "channel": "C123", "text": "bonjour"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body.get("reply")


def test_slack_ignores_bot_messages(anon_client):
    r = anon_client.post(
        "/api/v1/slack/webhook",
        json={
            "type": "event_callback",
            "event": {"type": "message", "channel": "C123", "text": "x", "bot_id": "B1"},
        },
    )
    assert r.json().get("skipped") is True


def test_slack_client_mock_keyless():
    import asyncio

    from app.messaging.slack import get_slack_client

    client = get_slack_client()
    res = asyncio.new_event_loop().run_until_complete(client.send_text("C1", "hello"))
    assert res.success and res.provider == "mock"
