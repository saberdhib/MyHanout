"""Ingestion des signaux externes (historique) vers `signal_observation`.

Tire les séries depuis le provider configuré (mock keyless par défaut) sur une
fenêtre de dates et upsert (idempotent par clé+région+date). Données publiques
→ table globale (pas de tenant).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.ingestion.signals_ext import DEFINITIONS, get_signal_provider
from app.models.signal import SignalObservation
from app.schemas.insights import SignalIngestResult

log = get_logger(__name__)


async def ingest_signals(
    session: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    region: str | None = None,
    keys: list[str] | None = None,
) -> SignalIngestResult:
    """Récupère et stocke les observations de signaux sur la fenêtre demandée."""
    today = date.today()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=180))
    region = region or settings.signals_region
    wanted = keys or [d[0] for d in DEFINITIONS]

    provider = get_signal_provider()
    inserted = 0
    for key in wanted:
        points = provider.fetch(key, date_from=date_from, date_to=date_to, region=region)
        for p in points:
            exists = await session.scalar(
                select(SignalObservation.id).where(
                    SignalObservation.signal_key == p.signal_key,
                    SignalObservation.region == (p.region or region),
                    SignalObservation.obs_date == p.obs_date,
                )
            )
            if exists:
                continue
            session.add(
                SignalObservation(
                    signal_key=p.signal_key,
                    region=p.region or region,
                    obs_date=p.obs_date,
                    value=p.value,
                    value_text=p.value_text,
                )
            )
            inserted += 1
    await session.flush()
    log.info("signals.ingest", provider=provider.name, series=len(wanted), observations=inserted)
    return SignalIngestResult(provider=provider.name, series=len(wanted), observations=inserted)
