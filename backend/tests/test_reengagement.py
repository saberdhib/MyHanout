"""Tests relance client : segmentation + envoi opt-in only (RGPD) + isolation."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.intelligence.reengagement.engine import Segment, classify
from app.models.customer import Customer
from app.models.loyalty import LoyaltyAccount, LoyaltyTransaction, LoyaltyTxnKind
from app.models.organization import Membership, MembershipRole, Organization
from app.models.user import User
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Moteur pur -------------------------------------------------------------


def test_engine_priority_reward_over_almost():
    d = classify(
        balance=120,
        threshold=100,
        days_since_last=0,
        reward_label="Bon",
        almost_gap=20,
        inactive_days=30,
    )
    assert d.segment == Segment.REWARD_READY


def test_engine_almost_and_inactive():
    almost = classify(
        balance=85,
        threshold=100,
        days_since_last=1,
        reward_label="Bon",
        almost_gap=20,
        inactive_days=30,
    )
    assert almost.segment == Segment.ALMOST_REWARD
    inactive = classify(
        balance=10,
        threshold=100,
        days_since_last=40,
        reward_label="Bon",
        almost_gap=20,
        inactive_days=30,
    )
    assert inactive.segment == Segment.INACTIVE
    none = classify(
        balance=10,
        threshold=100,
        days_since_last=1,
        reward_label="Bon",
        almost_gap=20,
        inactive_days=30,
    )
    assert none.segment is None


# --- Segmentation + envoi ---------------------------------------------------


async def _seed_customer(slug: str, *, name: str, balance: int, opt_in: bool, phone: str | None):
    async with TestSession() as s:
        org = await s.scalar(select(Organization).where(Organization.slug == slug))
        assert org is not None
        with tenant_context(org.id):
            c = Customer(name=name, phone=phone, consent_opt_in=opt_in)
            s.add(c)
            await s.flush()
            acc = LoyaltyAccount(customer_id=c.id, points_balance=balance, lifetime_points=balance)
            s.add(acc)
            await s.flush()
            s.add(
                LoyaltyTransaction(
                    account_id=acc.id,
                    customer_id=c.id,
                    kind=LoyaltyTxnKind.EARN,
                    points=balance,
                    amount=float(balance),
                    reason="seed",
                )
            )
            cid = c.id
            await s.commit()
    return cid


async def _new_org_with_owner(slug: str, owner_email: str) -> int:
    """Org dédiée (sans connecteur configuré → résolveur = client mock, zéro réseau)."""
    async with TestSession() as s:
        org = Organization(name=slug, slug=slug)
        s.add(org)
        await s.flush()
        u = User(email=owner_email, hashed_password=hash_password("secret"))
        s.add(u)
        await s.flush()
        s.add(Membership(user_id=u.id, organization_id=org.id, role=MembershipRole.OWNER))
        await s.commit()
        return org.id


def test_segments_and_optin_send(anon_client):
    # Org dédiée : évite qu'un connecteur WhatsApp configuré ailleurs (état sqlite partagé)
    # ne déclenche un vrai envoi réseau.
    _run(_new_org_with_owner("reeng-test", "reeng@test.local"))
    ready = _run(
        _seed_customer("reeng-test", name="Prêt", balance=150, opt_in=True, phone="+2126000001")
    )
    _run(
        _seed_customer(
            "reeng-test", name="No consent", balance=150, opt_in=False, phone="+2126000002"
        )
    )
    r = anon_client.post(
        "/api/v1/auth/login", json={"email": "reeng@test.local", "password": "secret"}
    )
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    segs = anon_client.get("/api/v1/reengagement/segments", headers=h).json()
    assert "opt-in" in segs["disclaimer"].lower()
    rr = next(s for s in segs["segments"] if s["segment"] == "reward_ready")
    ids = {c["customer_id"] for c in rr["customers"]}
    assert ready in ids
    assert rr["total"] == 2 and rr["contactable"] == 1

    # Envoi : seuls les opt-in avec téléphone sont contactés.
    res = anon_client.post(
        "/api/v1/reengagement/send", params={"segment": "reward_ready"}, headers=h
    ).json()
    assert res["sent"] == 1
    assert res["skipped_no_consent"] == 1


def test_send_unknown_segment_422(client):
    assert client.post("/api/v1/reengagement/send", params={"segment": "bogus"}).status_code == 422


def test_accountant_cannot_send(accountant_client):
    assert (
        accountant_client.post(
            "/api/v1/reengagement/send", params={"segment": "reward_ready"}
        ).status_code
        == 403
    )
