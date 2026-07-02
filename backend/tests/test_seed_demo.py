"""Mode démo blindé : le seed boucherie charge un commerce complet et idempotent."""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.core.tenancy import tenant_context
from app.db.seed_demo import DEMO_SLUG, seed_demo
from app.models import Customer, Invoice, Product, Sale
from app.models.base import MarkdownStatus
from app.models.markdown import MarkdownSuggestion
from app.models.organization import Organization
from app.models.reservation import Reservation
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _counts() -> dict[str, int]:
    async with TestSession() as s:
        org = await s.scalar(select(Organization).where(Organization.slug == DEMO_SLUG))
        assert org is not None
        with tenant_context(org.id):
            return {
                "products": await s.scalar(select(func.count()).select_from(Product)) or 0,
                "sales": await s.scalar(select(func.count()).select_from(Sale)) or 0,
                "invoices": await s.scalar(select(func.count()).select_from(Invoice)) or 0,
                "customers": await s.scalar(select(func.count()).select_from(Customer)) or 0,
                "reservations": await s.scalar(select(func.count()).select_from(Reservation)) or 0,
                "markdowns_applied": await s.scalar(
                    select(func.count())
                    .select_from(MarkdownSuggestion)
                    .where(MarkdownSuggestion.status == MarkdownStatus.APPLIED)
                )
                or 0,
            }


def test_seed_demo_lights_up_every_page():
    _run(seed_demo())
    counts = _run(_counts())

    # Catalogue boucherie + 3 mois de ventes → prévisions/backtest exploitables.
    assert counts["products"] == 14
    assert counts["sales"] > 500
    # Échéancier fournisseurs (payables) + clients fidèles + click&collect + démarque.
    assert counts["invoices"] == 7
    assert counts["customers"] == 4
    assert counts["reservations"] == 3
    # Human-in-the-loop : des démarques appliquées → cash récupéré dans l'Impact.
    assert counts["markdowns_applied"] >= 2


def test_seed_demo_is_idempotent():
    _run(seed_demo())
    before = _run(_counts())
    _run(seed_demo())  # 2e passage : ne double rien
    after = _run(_counts())
    assert before == after
