"""Signaux externes « compagnon du quotidien » : météo + tendances (mock keyless).

Providers abstraits, implémentation mock déterministe (aucun appel réseau). Un
provider réel (API météo, veille réseaux) se branche derrière la même interface.
Ces signaux enrichissent les recommandations (ex. chaleur → promo boissons).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel


class Weather(BaseModel):
    day: date
    temp_c: float
    condition: str  # ensoleillé | pluvieux | nuageux
    demand_hint: str  # impact attendu sur la demande


class Trend(BaseModel):
    topic: str
    score: float  # 0..1 popularité
    hint: str


class WeatherProvider(ABC):
    @abstractmethod
    def forecast(self, day: date) -> Weather: ...


class TrendsProvider(ABC):
    @abstractmethod
    def top(self, limit: int = 3) -> list[Trend]: ...


class MockWeatherProvider(WeatherProvider):
    def forecast(self, day: date) -> Weather:
        # Déterministe : varie avec le jour (sans hasard, reproductible en démo).
        temp = 18 + (day.toordinal() % 15)
        hot = temp >= 28
        return Weather(
            day=day,
            temp_c=float(temp),
            condition="ensoleillé" if hot else "nuageux",
            demand_hint="forte demande boissons/glaces" if hot else "demande standard",
        )


class MockTrendsProvider(TrendsProvider):
    _TRENDS = [
        Trend(topic="barbecue", score=0.82, hint="pousser viandes/charbon"),
        Trend(topic="batch cooking", score=0.61, hint="légumes/féculents en lot"),
        Trend(topic="zéro gaspi", score=0.55, hint="valoriser les fins de série"),
    ]

    def top(self, limit: int = 3) -> list[Trend]:
        return self._TRENDS[:limit]


class SignalsBundle(BaseModel):
    weather: Weather
    trends: list[Trend]


def get_signals(day: date | None = None) -> SignalsBundle:
    target = day or date.today()
    return SignalsBundle(
        weather=MockWeatherProvider().forecast(target),
        trends=MockTrendsProvider().top(),
    )
