"""Tests du Bilan hebdomadaire (agent Bilan)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

import app.models as m
from app.core.tenancy import tenant_context
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _seed_week_sales(slug: str = "org-a") -> None:
    """Ajoute des ventes datées d'aujourd'hui (dans la fenêtre du bilan)."""
    async with TestSession() as s:
        org = (await s.scalars(select(m.Organization).where(m.Organization.slug == slug))).first()
        assert org is not None
        with tenant_context(org.id):
            prod = (await s.scalars(select(m.Product).limit(1))).first()
            assert prod is not None
            now = datetime.now(UTC)
            for _ in range(3):
                s.add(
                    m.Sale(
                        product_id=prod.id,
                        quantity=2,
                        unit_price=float(prod.unit_price or 10),
                        total=float(prod.unit_price or 10) * 2,
                        sold_at=now,
                    )
                )
            await s.flush()
        await s.commit()


def test_weekly_report_structure(client):
    _run(_seed_week_sales())
    r = client.get("/api/v1/report/weekly")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["revenue"] > 0
    assert data["narrative"]
    assert data["highlights"] and data["actions"]
    assert data["period_start"] and data["period_end"]


def test_weekly_report_send(client):
    # Assure le fallback mock (un autre test a pu brancher un WhatsApp business).
    client.delete("/api/v1/connectors/manage/whatsapp")
    r = client.post("/api/v1/report/weekly/send")
    assert r.status_code == 200
    assert r.json()["narrative"]
