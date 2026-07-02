"""Tests du plan plateforme (backoffice cross-tenant) — Lot 2.

Vérifie la propriété la plus sensible : le plan plateforme voit TOUS les commerces
(l'inverse du garde-fou), mais SEULS les opérateurs MyHanout y accèdent, et un commerce
suspendu bloque ses utilisateurs. L'isolation tenant reste intacte pour les non-admins.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.models.platform import PlatformAdmin, PlatformRole
from app.models.user import User
from tests.conftest import TestSession


def _run(coro):
    # Event loop dédié (cf. CLAUDE.md §6 : ne pas réutiliser un loop stale).
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _ensure_platform_admin(email: str, password: str = "secret") -> None:
    async with TestSession() as s:
        with tenant_context(None):
            existing = await s.scalar(select(User).where(User.email == email))
            if existing is None:
                u = User(email=email, hashed_password=hash_password(password))
                s.add(u)
                await s.flush()
                s.add(PlatformAdmin(user_id=u.id, role=PlatformRole.SUPERADMIN, is_active=True))
                await s.commit()


@pytest.fixture
def platform_client(anon_client):
    """Client authentifié en tant qu'opérateur plateforme (superadmin)."""
    _run(_ensure_platform_admin("ops@myhanout.local"))
    r = anon_client.post(
        "/api/v1/auth/login", json={"email": "ops@myhanout.local", "password": "secret"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["platform_role"] == "superadmin"
    anon_client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return anon_client


def _bearer(anon_client, email: str, password: str = "secret") -> dict:
    r = anon_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- Accès cross-tenant réservé aux opérateurs -------------------------------


def test_platform_admin_sees_all_orgs(platform_client):
    r = platform_client.get("/api/v1/platform/clients")
    assert r.status_code == 200, r.text
    slugs = {c["slug"] for c in r.json()["items"]}
    assert {"org-a", "org-b"} <= slugs  # cross-tenant : voit les deux commerces


def test_overview_aggregates_parc(platform_client):
    r = platform_client.get("/api/v1/platform/overview")
    assert r.status_code == 200
    assert r.json()["clients_total"] >= 2


def test_tenant_user_cannot_access_platform(client):
    # Owner de l'org A, mais PAS opérateur plateforme -> 403.
    assert client.get("/api/v1/platform/clients").status_code == 403


def test_anon_cannot_access_platform(anon_client):
    assert anon_client.get("/api/v1/platform/clients").status_code == 401


# --- Provisioning ------------------------------------------------------------


def test_provision_creates_empty_accessible_org(platform_client):
    payload = {
        "name": "Boulangerie Test",
        "slug": "boul-test",
        "business_type": "boulangerie",
        "owner_email": "boul@test.local",
        "owner_password": "secret123",
        "plan": "starter",
    }
    r = platform_client.post("/api/v1/platform/clients", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "active"  # plan payant -> actif
    assert body["products"] == 0  # commerce vierge

    # Le nouvel owner peut se connecter et est bien isolé sur son org (vide).
    headers = _bearer(platform_client, "boul@test.local", "secret123")
    me = platform_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    stocks = platform_client.get("/api/v1/stocks", headers=headers)
    assert stocks.json()["items"] == []


def test_provision_duplicate_slug_conflicts(platform_client):
    payload = {
        "name": "Dup",
        "slug": "dup-test",
        "owner_email": "dup@test.local",
        "owner_password": "secret123",
        "plan": "starter",
    }
    assert platform_client.post("/api/v1/platform/clients", json=payload).status_code == 201
    # Deuxième fois : slug déjà pris.
    assert platform_client.post("/api/v1/platform/clients", json=payload).status_code == 409


# --- Cycle de vie : suspension bloque l'accès tenant -------------------------


def test_suspend_blocks_tenant_access(platform_client):
    payload = {
        "name": "Susp Test",
        "slug": "susp-test",
        "owner_email": "susp@test.local",
        "owner_password": "secret123",
        "plan": "starter",
    }
    r = platform_client.post("/api/v1/platform/clients", json=payload)
    assert r.status_code == 201, r.text
    org_id = r.json()["organization_id"]

    headers = _bearer(platform_client, "susp@test.local", "secret123")
    assert platform_client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # Suspension via le backoffice.
    s = platform_client.post(
        f"/api/v1/platform/clients/{org_id}/status", json={"status": "suspended"}
    )
    assert s.status_code == 200, s.text
    assert s.json()["status"] == "suspended"

    # Même token : l'accès tenant est désormais refusé.
    assert platform_client.get("/api/v1/auth/me", headers=headers).status_code == 403


# --- Billing -----------------------------------------------------------------


def test_set_plan_updates_mrr(platform_client):
    payload = {
        "name": "Plan Test",
        "slug": "plan-test",
        "owner_email": "plan@test.local",
        "owner_password": "secret123",
        "plan": "starter",
    }
    org_id = platform_client.post("/api/v1/platform/clients", json=payload).json()[
        "organization_id"
    ]
    r = platform_client.post(
        f"/api/v1/platform/clients/{org_id}/plan",
        json={"plan": "pro", "mrr_eur": 99.0, "subscription_status": "active"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "pro"
    assert r.json()["mrr_eur"] == 99.0


# --- Audit : les actions plateforme sont tracées -----------------------------


def test_platform_actions_are_audited(platform_client):
    payload = {
        "name": "Audit Test",
        "slug": "audit-test",
        "owner_email": "audit@test.local",
        "owner_password": "secret123",
        "plan": "starter",
    }
    assert platform_client.post("/api/v1/platform/clients", json=payload).status_code == 201

    async def _count_audit() -> int:
        from app.models.audit_log import AuditLog

        async with TestSession() as s:
            with tenant_context(None):
                rows = await s.scalars(
                    select(AuditLog).where(AuditLog.action == "platform.provision_client")
                )
                return len(list(rows))

    assert _run(_count_audit()) >= 1
