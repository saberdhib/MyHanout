"""Signaux **métier du commerçant** — adaptateurs derrière une interface propre.

Le différenciateur MyHanout : le commerçant connaît son quartier mieux qu'une API
nationale (match du club local, jour de paie le 5, braderie, fête religieuse…).
Ces signaux sont **tenant** (`ExternalSignal`) et croisés par le moteur de reco
avec les séries publiques génériques.

Règle d'or : ABC + mock keyless par défaut. Brancher de vraies sources plus tard
ne change que l'implémentation (le reste — ingestion, reco — est générique).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta

from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger
from app.models.base import SignalKind

log = get_logger(__name__)


class MerchantSignalPoint(BaseModel):
    key: str
    label: str
    kind: SignalKind
    signal_date: date
    value: float = 1.0
    value_text: str | None = None
    scope: str | None = None


# Catalogue des signaux métier livrés en mock (le commerçant peut en ajouter d'autres).
_CATALOG: list[tuple[str, str, SignalKind, str | None]] = [
    ("match_local", "Match du club local", SignalKind.SPORTS, "quartier"),
    ("paie_5", "Jour de paie (le 5)", SignalKind.ECONOMIC, "quartier"),
    ("jour_marche", "Jour de marché", SignalKind.CUSTOM, "quartier"),
    ("fete_religieuse", "Fête religieuse", SignalKind.HOLIDAY, "quartier"),
    ("braderie", "Braderie / animation", SignalKind.CUSTOM, "quartier"),
]


class SignalSource(ABC):
    """Source de signaux métier (mock par défaut, vraies sources brançables)."""

    name: str = "abstract"

    @abstractmethod
    def fetch(self, *, date_from: date, date_to: date) -> list[MerchantSignalPoint]: ...


class MockSignalSource(SignalSource):
    """Génère des signaux déterministes (sans réseau) pour démo & tests."""

    name = "mock"

    def fetch(self, *, date_from: date, date_to: date) -> list[MerchantSignalPoint]:
        out: list[MerchantSignalPoint] = []
        d = date_from
        while d <= date_to:
            ordinal = d.toordinal()
            # Match local : samedis des semaines paires (affluence snacks/boissons).
            if d.weekday() == 5 and (ordinal // 7) % 2 == 0:
                out.append(self._pt("match_local", d, value_text="match à domicile"))
            # Jour de paie : le 5 de chaque mois (pic de pouvoir d'achat).
            if d.day == 5:
                out.append(self._pt("paie_5", d))
            # Jour de marché : mercredi et samedi (flux piéton).
            if d.weekday() in (2, 5):
                out.append(self._pt("jour_marche", d))
            # Braderie : 1er dimanche du mois.
            if d.weekday() == 6 and d.day <= 7:
                out.append(self._pt("braderie", d))
            d += timedelta(days=1)
        return out

    def _pt(self, key: str, d: date, *, value_text: str | None = None) -> MerchantSignalPoint:
        label, kind, scope = next((c[1], c[2], c[3]) for c in _CATALOG if c[0] == key)
        return MerchantSignalPoint(
            key=key,
            label=label,
            kind=kind,
            signal_date=d,
            value=1.0,
            value_text=value_text,
            scope=scope,
        )


def get_signal_source() -> SignalSource:
    """Source configurée. Défaut : mock (keyless)."""
    # Point d'extension : ajouter d'autres impls (http, ICS calendrier…) ici.
    if settings.merchant_signals_source.lower() != "mock":
        log.warning("merchant_signals.fallback", to="mock")
    return MockSignalSource()


__all__ = ["MerchantSignalPoint", "SignalSource", "get_signal_source"]
