"""Tests du registre de modèles MLOps (Lot 5) — versionnement + dérive + isolation."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.tenancy import tenant_context
from app.models.model_artifact import RetrainTrigger
from app.models.organization import Organization
from app.services import model_registry_service as reg
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _org_id(slug: str) -> int:
    async with TestSession() as s:
        org = await s.scalar(select(Organization).where(Organization.slug == slug))
        assert org is not None
        return org.id


def test_retrain_versions_and_single_active():
    org_id = _run(_org_id("org-a"))

    async def _scenario():
        async with TestSession() as s:
            with tenant_context(org_id):
                # Produit seedé de l'org A (id 1 : BOEUF-HACHE).
                a1 = await reg.retrain_product(s, 1, trigger=RetrainTrigger.MANUAL)
                await s.commit()
                a2 = await reg.retrain_product(s, 1, trigger=RetrainTrigger.SCHEDULED)
                await s.commit()
                assert a1.version != a2.version  # versions incrémentées
                # Artefact sérialisé + stocké (mock keyless → URI déterministe).
                assert a2.artifact_uri and a2.artifact_uri.startswith("mock://")
                actives = await reg.list_models(s, 1, active_only=True)
                assert len(actives) == 1  # un seul actif
                assert actives[0].id == a2.id
                assert actives[0].active is True

    _run(_scenario())


def test_registry_tenant_isolation():
    org_a = _run(_org_id("org-a"))
    org_b = _run(_org_id("org-b"))

    async def _scenario():
        async with TestSession() as s:
            with tenant_context(org_a):
                await reg.retrain_product(s, 1, trigger=RetrainTrigger.MANUAL)
                await s.commit()
        async with TestSession() as s:
            # L'org B ne voit AUCUN modèle de l'org A (garde-fou).
            with tenant_context(org_b):
                rows = await reg.list_models(s)
                assert all(r.organization_id == org_b for r in rows)

    _run(_scenario())


def test_drift_triggers_retrain():
    """Un produit dont la MAPE dépasse le seuil est réentraîné (trigger=drift)."""
    org_id = _run(_org_id("org-a"))

    async def _scenario():
        async with TestSession() as s:
            with tenant_context(org_id):
                # Injecte une évaluation à forte erreur (MAPE 100%) sur un produit dédié.
                import datetime

                from app.models.forecast_evaluation import ForecastEvaluation
                from app.models.product import Product

                p = Product(sku=f"DRIFT-{id(s)}", name="Drift", unit="kg")
                s.add(p)
                await s.flush()
                s.add(
                    ForecastEvaluation(
                        product_id=p.id,
                        eval_date=datetime.date(2026, 6, 1),
                        predicted=10,
                        actual=5,
                        error_abs=5,
                        error_pct=1.0,  # MAPE 100% > seuil
                        model="naive",
                        model_version="naive-v1",
                    )
                )
                await s.commit()
                retrained = await reg.retrain_on_drift(s, mape_threshold=0.35)
                await s.commit()
                assert any(a.product_id == p.id for a in retrained)
                assert all(a.trigger == RetrainTrigger.DRIFT for a in retrained)

    _run(_scenario())
