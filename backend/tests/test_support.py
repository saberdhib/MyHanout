"""Tests Support & mises à jour (Lot 3).

- Le commerçant ne voit que SES tickets (garde-fou) ; l'opérateur les voit tous.
- Un échange ticket fonctionne des deux côtés + estampillage cross-tenant correct.
- Les notes de version non publiées restent invisibles aux commerçants.

NB : on multiplexe plusieurs identités sur un seul client via des en-têtes explicites
par requête (éviter le partage d'en-tête entre fixtures d'auth sur le même client).
"""

from __future__ import annotations

import asyncio

from tests.conftest import _ensure_platform_admin


def _headers(anon_client, email: str, password: str = "secret") -> dict:
    r = anon_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _platform_headers(anon_client) -> dict:
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_ensure_platform_admin())
    finally:
        loop.close()
    return _headers(anon_client, "ops@myhanout.local")


def _open_ticket(anon_client, headers, subject="Problème de connexion caisse") -> int:
    r = anon_client.post(
        "/api/v1/support/tickets",
        headers=headers,
        json={"subject": subject, "body": "Ma caisse ne remonte plus les ventes."},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- Côté commerçant --------------------------------------------------------


def test_merchant_creates_and_reads_ticket(anon_client):
    h = _headers(anon_client, "admin@test.local")
    tid = _open_ticket(anon_client, h)
    got = anon_client.get(f"/api/v1/support/tickets/{tid}", headers=h)
    assert got.status_code == 200
    body = got.json()
    assert body["status"] == "open"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["author_kind"] == "merchant"


def test_ticket_isolation_between_orgs(anon_client):
    ha = _headers(anon_client, "admin@test.local")
    hb = _headers(anon_client, "owner@b.local")
    tid = _open_ticket(anon_client, ha, subject="Ticket org A")
    # L'org B ne doit PAS voir le ticket de l'org A (garde-fou).
    assert anon_client.get(f"/api/v1/support/tickets/{tid}", headers=hb).status_code == 404
    subjects = {
        t["subject"] for t in anon_client.get("/api/v1/support/tickets", headers=hb).json()["items"]
    }
    assert "Ticket org A" not in subjects


# --- Côté plateforme --------------------------------------------------------


def test_platform_sees_all_tickets_and_replies(anon_client):
    hp = _platform_headers(anon_client)
    hm = _headers(anon_client, "admin@test.local")
    tid = _open_ticket(anon_client, hm, subject="Question facturation")

    # L'opérateur voit le ticket cross-tenant.
    all_tickets = anon_client.get("/api/v1/platform/tickets", headers=hp).json()["items"]
    assert any(t["id"] == tid for t in all_tickets)

    # Il répond : le ticket passe en "pending" + message côté plateforme.
    r = anon_client.post(
        f"/api/v1/platform/tickets/{tid}/reply",
        headers=hp,
        json={"body": "Bonjour, on regarde."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"
    assert "platform" in [m["author_kind"] for m in r.json()["messages"]]

    # Le commerçant voit la réponse et peut relancer (rouvre le ticket).
    reopened = anon_client.post(
        f"/api/v1/support/tickets/{tid}/messages", headers=hm, json={"body": "Merci !"}
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"


def test_platform_resolves_ticket(anon_client):
    hp = _platform_headers(anon_client)
    hm = _headers(anon_client, "admin@test.local")
    tid = _open_ticket(anon_client, hm, subject="À résoudre")
    r = anon_client.post(
        f"/api/v1/platform/tickets/{tid}/status", headers=hp, json={"status": "resolved"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_tenant_user_cannot_access_platform_tickets(anon_client):
    hm = _headers(anon_client, "admin@test.local")
    assert anon_client.get("/api/v1/platform/tickets", headers=hm).status_code == 403


# --- Notes de version -------------------------------------------------------


def test_release_note_visible_only_after_publish(anon_client):
    hp = _platform_headers(anon_client)
    hm = _headers(anon_client, "admin@test.local")
    created = anon_client.post(
        "/api/v1/platform/releases",
        headers=hp,
        json={"version": "9.9", "title": "Nouveauté test", "body": "détails"},
    )
    assert created.status_code == 201, created.text
    note_id = created.json()["id"]
    assert created.json()["published"] is False

    # Tant que non publiée : invisible côté commerçant.
    versions = {
        n["version"] for n in anon_client.get("/api/v1/releases", headers=hm).json()["items"]
    }
    assert "9.9" not in versions

    # Après publication : visible.
    pub = anon_client.post(f"/api/v1/platform/releases/{note_id}/publish", headers=hp)
    assert pub.status_code == 200
    assert pub.json()["published"] is True
    versions = {
        n["version"] for n in anon_client.get("/api/v1/releases", headers=hm).json()["items"]
    }
    assert "9.9" in versions
