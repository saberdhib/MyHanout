"""Signaux externes historiques — abstraction + mock keyless par défaut.

Chaque source (météo, vacances scolaires, prix carburant, matchs de foot, indices
éco) est un **provider** derrière une ABC. Sans clé → mock déterministe (séries
reproductibles, zéro réseau). Avec clé (`.env`) → impl HTTP réelle.

Point d'extension : pour ajouter une source, déclarer une `SignalDefinition` + une
impl de `ExternalSignalProvider` ; le reste (ingestion, corrélation) est générique.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import date, timedelta

from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger
from app.models.base import SignalKind

log = get_logger(__name__)

# Registre canonique des séries livrées par défaut (clé, libellé, type, unité, provider).
# `seed_signal_definitions` les insère ; l'admin peut en ajouter d'autres.
DEFINITIONS: list[tuple[str, str, SignalKind, str | None]] = [
    ("weather_temp_c", "Température (°C)", SignalKind.WEATHER, "°C"),
    ("weather_rain", "Pluie (0/1)", SignalKind.WEATHER, "bool"),
    ("school_holiday", "Vacances scolaires (0/1)", SignalKind.HOLIDAY, "bool"),
    ("public_holiday", "Jour férié (0/1)", SignalKind.HOLIDAY, "bool"),
    ("fuel_price_eur_l", "Prix carburant (€/L)", SignalKind.FUEL, "€/L"),
    ("football_match", "Match de foot local (0/1)", SignalKind.SPORTS, "bool"),
]


class SignalPoint(BaseModel):
    signal_key: str
    obs_date: date
    value: float
    value_text: str | None = None
    region: str | None = None


class ExternalSignalProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def fetch(
        self, signal_key: str, *, date_from: date, date_to: date, region: str | None = None
    ) -> list[SignalPoint]:
        raise NotImplementedError


class MockSignalProvider(ExternalSignalProvider):
    """Séries déterministes (saisonnalité + motifs), sans réseau — pour démo & tests."""

    name = "mock"

    def fetch(self, signal_key, *, date_from, date_to, region=None):
        points: list[SignalPoint] = []
        d = date_from
        while d <= date_to:
            ordinal = d.toordinal()
            doy = d.timetuple().tm_yday
            if signal_key == "weather_temp_c":
                # Saisonnalité annuelle + petite oscillation déterministe.
                val = 15 + 10 * math.sin(2 * math.pi * (doy - 80) / 365) + (ordinal % 3)
            elif signal_key == "weather_rain":
                val = float(ordinal % 4 == 0)
            elif signal_key == "school_holiday":
                # Approx : fév, avril, juillet-août, fin déc.
                val = float(d.month in (7, 8) or (d.month == 12 and d.day >= 20))
            elif signal_key == "public_holiday":
                val = float((d.month, d.day) in {(1, 1), (5, 1), (7, 14), (12, 25)})
            elif signal_key == "fuel_price_eur_l":
                val = 1.80 + 0.15 * math.sin(2 * math.pi * doy / 365) + (ordinal % 5) * 0.01
            elif signal_key == "football_match":
                val = float(d.weekday() in (5, 6) and (ordinal % 2 == 0))  # week-ends pairs
            else:
                val = 0.0
            points.append(
                SignalPoint(signal_key=signal_key, obs_date=d, value=round(val, 3), region=region)
            )
            d += timedelta(days=1)
        return points


class HttpSignalProvider(ExternalSignalProvider):
    """Provider HTTP générique : GET {base}/{signal_key}?from=&to=&region=. Env-driven."""

    name = "http"

    def fetch(self, signal_key, *, date_from, date_to, region=None):  # pragma: no cover - réseau
        import httpx

        resp = httpx.get(
            f"{settings.signals_http_url}/{signal_key}",
            params={"from": date_from.isoformat(), "to": date_to.isoformat(), "region": region},
            headers=(
                {"Authorization": f"Bearer {settings.signals_api_key}"}
                if settings.signals_api_key
                else {}
            ),
            timeout=30,
        )
        resp.raise_for_status()
        return [SignalPoint(signal_key=signal_key, **row) for row in resp.json()]


def get_signal_provider() -> ExternalSignalProvider:
    """Provider configuré. Sans URL → mock (keyless)."""
    if settings.signals_provider.lower() == "http" and settings.signals_http_url:
        return HttpSignalProvider()
    if settings.signals_provider.lower() == "http":
        log.warning("signals_ext.provider.fallback", reason="no url", to="mock")
    return MockSignalProvider()


async def seed_signal_definitions(session) -> int:
    """Upsert idempotent du registre des séries (par clé)."""
    from sqlalchemy import select

    from app.models.signal import SignalDefinition

    created = 0
    for key, label, kind, unit in DEFINITIONS:
        exists = await session.scalar(select(SignalDefinition).where(SignalDefinition.key == key))
        if exists is None:
            session.add(
                SignalDefinition(key=key, label=label, kind=kind, unit=unit, provider="mock")
            )
            created += 1
    await session.flush()
    return created


__all__ = [
    "DEFINITIONS",
    "ExternalSignalProvider",
    "SignalPoint",
    "get_signal_provider",
    "seed_signal_definitions",
]
