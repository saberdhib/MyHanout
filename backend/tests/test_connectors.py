"""Tests connecteurs par commerce (modèle B) : chiffrement, CRUD, résolution, isolation."""

from __future__ import annotations

import asyncio

from app.core.crypto import decrypt, encrypt
from app.core.tenancy import tenant_context
from app.messaging.resolver import resolve_whatsapp_client
from tests.conftest import TestSession, _login


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Chiffrement ------------------------------------------------------------
def test_crypto_round_trip():
    token = encrypt("super-secret-token")
    assert token != "super-secret-token"  # bien chiffré
    assert decrypt(token) == "super-secret-token"


# --- API : enregistrement + statut sans secret ------------------------------
def test_connector_upsert_hides_secret(client):
    r = client.put(
        "/api/v1/connectors/manage/whatsapp",
        json={
            "fields": {
                "phone_number_id": "123456",
                "access_token": "EAAG-secret",
                "app_secret": "appsec",
            },
            "active": True,
        },
    )
    assert r.status_code == 200, r.text
    st = r.json()
    assert st["configured"] is True
    assert st["has_secret"] is True
    assert st["public"]["phone_number_id"] == "123456"
    # Aucun secret renvoyé.
    assert "access_token" not in str(st["public"])

    listed = client.get("/api/v1/connectors/manage").json()
    wa = next(c for c in listed if c["kind"] == "whatsapp")
    assert wa["configured"] and wa["active"]


def test_connector_partial_update_keeps_secret(client):
    client.put(
        "/api/v1/connectors/manage/telegram",
        json={"fields": {"bot_token": "123:ABC"}, "active": True},
    )
    # Maj sans renvoyer le token (champ vide) → le secret est conservé.
    client.put("/api/v1/connectors/manage/telegram", json={"fields": {}, "active": True})
    st = next(c for c in client.get("/api/v1/connectors/manage").json() if c["kind"] == "telegram")
    assert st["configured"] is True  # token toujours là


def test_connector_owner_only(viewer_client):
    r = viewer_client.put(
        "/api/v1/connectors/manage/slack",
        json={"fields": {"bot_token": "xoxb-x"}, "active": True},
    )
    assert r.status_code == 403


def test_connector_delete(client):
    client.put(
        "/api/v1/connectors/manage/slack",
        json={"fields": {"bot_token": "xoxb-x"}, "active": True},
    )
    assert client.delete("/api/v1/connectors/manage/slack").status_code == 204
    st = next(c for c in client.get("/api/v1/connectors/manage").json() if c["kind"] == "slack")
    assert st["configured"] is False


# --- Résolveur : la config du tenant prime sur le global --------------------
def test_resolver_uses_tenant_credentials(client):
    from sqlalchemy import select

    import app.models as m

    client.put(
        "/api/v1/connectors/manage/whatsapp",
        json={
            "fields": {"phone_number_id": "999", "access_token": "tok-tenant"},
            "active": True,
        },
    )

    async def check():
        async with TestSession() as s:
            org = (
                await s.scalars(select(m.Organization).where(m.Organization.slug == "org-a"))
            ).first()
            with tenant_context(org.id):
                wa = await resolve_whatsapp_client(s)
                return getattr(wa, "name", "mock"), getattr(wa, "phone_id", None)

    name, phone_id = _run(check())
    assert name == "business"  # vrai client, pas le mock
    assert phone_id == "999"  # identifiants DU commerce


# --- Isolation tenant -------------------------------------------------------
def test_connectors_isolated_between_tenants(anon_client):
    a = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {a}"
    anon_client.put(
        "/api/v1/connectors/manage/whatsapp",
        json={"fields": {"phone_number_id": "A1", "access_token": "tok-a"}, "active": True},
    )

    b = _login(anon_client, "owner@b.local")
    anon_client.headers["Authorization"] = f"Bearer {b}"
    wa_b = next(
        c for c in anon_client.get("/api/v1/connectors/manage").json() if c["kind"] == "whatsapp"
    )
    # B ne voit PAS la config de A.
    assert wa_b["configured"] is False
    assert wa_b["public"].get("phone_number_id") != "A1"
