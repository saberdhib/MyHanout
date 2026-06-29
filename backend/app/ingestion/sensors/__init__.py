"""Capteurs de température (chaîne du froid) — abstraction + mock keyless.

Sans thermomètre connecté → `MockSensorProvider` (relevés déterministes, zéro
réseau). Avec capteurs réels → `http` (passerelle qui expose les relevés). La
sélection se fait par env ; sans config on reste en mock.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class SensorReading(BaseModel):
    sensor_external_id: str
    temp_c: float
    source: str = "mock"


class SensorProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def read(self, sensor_external_id: str, *, kind: str) -> SensorReading:
        """Relève la température d'un capteur (par identifiant externe)."""
        raise NotImplementedError


class MockSensorProvider(SensorProvider):
    """Relevés déterministes : la plupart dans la plage, une dérive reproductible.

    Pas de hasard (démo stable) : la valeur dépend de l'identifiant + du type.
    Un capteur dont l'id contient « hot » simule une dérive (frigo qui monte).
    """

    name = "mock"

    async def read(self, sensor_external_id: str, *, kind: str) -> SensorReading:
        base = {"fridge": 3.0, "freezer": -18.0, "oven": 200.0, "other": 20.0}.get(kind, 3.0)
        # Petit décalage déterministe à partir de l'identifiant.
        drift = (sum(ord(c) for c in sensor_external_id) % 5) - 2  # -2..+2
        temp = base + drift
        if "hot" in sensor_external_id.lower():  # capteur volontairement en dérive (démo)
            temp = base + 6
        return SensorReading(sensor_external_id=sensor_external_id, temp_c=float(temp))


class HttpSensorProvider(SensorProvider):
    """Passerelle HTTP : GET {url}/{id} -> {"temp_c": ...}. Activée par env."""

    name = "http"

    async def read(
        self, sensor_external_id: str, *, kind: str
    ) -> SensorReading:  # pragma: no cover
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.sensor_http_url}/{sensor_external_id}")
            resp.raise_for_status()
            data = resp.json()
        return SensorReading(
            sensor_external_id=sensor_external_id, temp_c=float(data["temp_c"]), source="http"
        )


def get_sensor_provider() -> SensorProvider:
    """Retourne le provider de capteurs configuré. Sans config → mock (keyless)."""
    if settings.sensor_provider.lower() == "http" and settings.sensor_http_url:
        return HttpSensorProvider()
    if settings.sensor_provider.lower() == "http":
        log.warning("sensors.provider.fallback", reason="no url", to="mock")
    return MockSensorProvider()


__all__ = ["SensorProvider", "SensorReading", "get_sensor_provider"]
