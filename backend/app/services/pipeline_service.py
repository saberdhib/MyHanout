"""Orchestration des pipelines data (Brique 1) — explicite, observable, traçable.

Choix : **Celery + un modèle `PipelineRun`** plutôt qu'un orchestrateur lourd
(Dagster). Justification : on reste dans l'écosystème déjà présent (Celery/Redis),
zéro nouvelle infra, exécutable in-process (donc testable sur sqlite, keyless), et
chaque donnée produite référence le `pipeline_run_id` qui l'a générée.

Un *job* = une suite d'*assets* exécutés sous un même run. Les assets réels
(snapshot stock, ingestion signaux métier, recommandations, alertes) écrivent des
lignes tenant estampillées par le garde-fou ; le run agrège rows + fraîcheur.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.events import publish_event
from app.core.logging import get_logger
from app.core.metrics import PIPELINE_DURATION, PIPELINE_RUNS
from app.core.tenancy import get_current_org
from app.ingestion.merchant_signals import get_signal_source
from app.models.base import PipelineStatus, PipelineTrigger
from app.models.external_signal import ExternalSignal
from app.models.inventory import InventorySnapshot
from app.models.pipeline import PipelineRun
from app.models.product import Product
from app.repositories.stock import StockRepository
from app.services.alert_service import scan_alerts
from app.services.recommendation_service import compute_recommendations

log = get_logger(__name__)

Asset = Callable[[AsyncSession, PipelineRun, date], Awaitable[int]]


async def _asset_snapshot_inventory(session: AsyncSession, run: PipelineRun, today: date) -> int:
    """Capture l'état du stock du jour (point-in-time), idempotent par produit/date."""
    stock_repo = StockRepository(session)
    products = list((await session.scalars(select(Product.id))).all())
    rows = 0
    for pid in products:
        exists = await session.scalar(
            select(InventorySnapshot.id).where(
                InventorySnapshot.product_id == pid,
                InventorySnapshot.snapshot_date == today,
            )
        )
        stocks = await stock_repo.list_for_product(pid)
        qty = float(sum(float(s.quantity) for s in stocks))
        threshold = float(max((float(s.reorder_threshold) for s in stocks), default=0.0))
        if exists:
            snap = await session.get(InventorySnapshot, exists)
            if snap:
                snap.quantity = qty
                snap.reorder_threshold = threshold
                snap.pipeline_run_id = run.id
        else:
            session.add(
                InventorySnapshot(
                    product_id=pid,
                    snapshot_date=today,
                    quantity=qty,
                    reorder_threshold=threshold,
                    pipeline_run_id=run.id,
                )
            )
            rows += 1
    await session.flush()
    publish_event(get_current_org(), "inventory_updated", {"snapshots": rows})
    return rows


async def _asset_ingest_signals(session: AsyncSession, run: PipelineRun, today: date) -> int:
    """Ingestion des signaux **métier** du commerçant (mock), idempotent par clé/date."""
    source = get_signal_source()
    points = source.fetch(date_from=today - timedelta(days=30), date_to=today + timedelta(days=30))
    rows = 0
    for p in points:
        exists = await session.scalar(
            select(ExternalSignal.id).where(
                ExternalSignal.key == p.key, ExternalSignal.signal_date == p.signal_date
            )
        )
        if exists:
            continue
        session.add(
            ExternalSignal(
                key=p.key,
                label=p.label,
                kind=p.kind,
                signal_date=p.signal_date,
                value=p.value,
                value_text=p.value_text,
                source="merchant",
                scope=p.scope,
            )
        )
        rows += 1
    await session.flush()
    return rows


async def _asset_recommend(session: AsyncSession, run: PipelineRun, today: date) -> int:
    decisions = await compute_recommendations(
        session, persist=True, pipeline_run_id=run.id, today=today
    )
    publish_event(get_current_org(), "forecast_ready", {"recommendations": len(decisions)})
    return len(decisions)


async def _asset_scan_alerts(session: AsyncSession, run: PipelineRun, today: date) -> int:
    created = await scan_alerts(session, pipeline_run_id=run.id, today=today)
    return len(created)


# Registre des jobs : un job = une suite d'assets exécutés sous un même run.
JOBS: dict[str, list[Asset]] = {
    "snapshot_inventory": [_asset_snapshot_inventory],
    "ingest_signals": [_asset_ingest_signals],
    "recommend": [_asset_recommend],
    "scan_alerts": [_asset_scan_alerts],
    "daily": [
        _asset_snapshot_inventory,
        _asset_ingest_signals,
        _asset_recommend,
        _asset_scan_alerts,
    ],
}


def available_jobs() -> list[str]:
    return list(JOBS.keys())


async def run_job(
    session: AsyncSession,
    job_name: str,
    *,
    trigger: PipelineTrigger = PipelineTrigger.MANUAL,
    user_id: int | None = None,
    today: date | None = None,
) -> PipelineRun:
    """Exécute un job sous un `PipelineRun` traçable (status, rows, fraîcheur, erreur)."""
    if job_name not in JOBS:
        raise ValueError(f"job inconnu : {job_name}")
    today = today or date.today()
    now = datetime.now(UTC)

    run = PipelineRun(
        job_name=job_name,
        status=PipelineStatus.RUNNING,
        trigger=trigger,
        started_at=now,
        triggered_by_user_id=user_id,
    )
    session.add(run)
    await session.flush()  # id + organization_id estampillés

    total = 0
    counts: dict[str, int] = {}
    try:
        for asset in JOBS[job_name]:
            rows = await asset(session, run, today)
            counts[asset.__name__] = rows
            total += rows
        run.status = PipelineStatus.SUCCESS
    except Exception as exc:  # un asset échoue → run failed, on trace l'erreur
        run.status = PipelineStatus.FAILED
        run.error = str(exc)
        log.warning("pipeline.failed", job=job_name, run_id=run.id, error=str(exc))
    finally:
        finished = datetime.now(UTC)
        run.finished_at = finished
        run.rows_processed = total
        run.data_freshness_at = finished
        run.detail = json.dumps(counts, ensure_ascii=False)
        await session.flush()
        PIPELINE_RUNS.labels(job=job_name, status=str(run.status)).inc()
        PIPELINE_DURATION.labels(job=job_name).observe((finished - now).total_seconds())

    publish_event(
        get_current_org(),
        "pipeline_finished",
        {"id": run.id, "job": job_name, "status": str(run.status), "rows": total},
    )
    log.info(
        "pipeline.run",
        job=job_name,
        run_id=run.id,
        status=str(run.status),
        rows=total,
        trigger=str(trigger),
    )
    return run


def _duration_ms(run: PipelineRun) -> int | None:
    if run.started_at and run.finished_at:
        return int((run.finished_at - run.started_at).total_seconds() * 1000)
    return None


async def list_runs(
    session: AsyncSession,
    *,
    job_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[PipelineRun]:
    stmt = select(PipelineRun).order_by(PipelineRun.id.desc()).limit(limit)
    if job_name:
        stmt = stmt.where(PipelineRun.job_name == job_name)
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    return list((await session.scalars(stmt)).all())


async def health(session: AsyncSession):
    """Dernier run + fraîcheur par job (pour la page Data Ops)."""
    from app.schemas.dataplatform import PipelineHealth, PipelineJobHealth

    jobs: list[PipelineJobHealth] = []
    stale = 0
    for job_name in JOBS:
        last = await session.scalar(
            select(PipelineRun)
            .where(PipelineRun.job_name == job_name)
            .order_by(PipelineRun.id.desc())
            .limit(1)
        )
        if last is None:
            jobs.append(PipelineJobHealth(job_name=job_name))
            stale += 1
            continue
        from app.services.alert_service import is_stale

        if is_stale(last.data_freshness_at):
            stale += 1
        jobs.append(
            PipelineJobHealth(
                job_name=job_name,
                last_status=str(last.status),
                last_run_at=last.finished_at or last.started_at,
                data_freshness_at=last.data_freshness_at,
                last_error=last.error,
            )
        )
    explanation = (
        f"{len(jobs)} job(s) suivis ; {stale} sans run récent (fraîcheur > "
        f"{settings.forecast_horizon_days} j ignorée ici, seuil data_stale appliqué)."
    )
    return PipelineHealth(jobs=jobs, explanation=explanation)
