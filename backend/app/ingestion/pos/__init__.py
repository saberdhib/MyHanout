"""Connecteur caisse (POS) — abstraction + mock keyless.

Permet d'ingérer les ventes en quasi temps réel depuis la caisse du commerçant,
sans saisie. Sans caisse branchée → `MockPOSConnector` (ventes factices,
déterministes). Avec une vraie caisse → `http` (poll d'un endpoint). Les ventes
poussées via webhook passent par le même service d'ingestion (idempotent).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class POSSale(BaseModel):
    external_ref: str  # identifiant ticket/ligne côté caisse (idempotence)
    sku: str
    quantity: float
    unit_price: float
    sold_at: datetime


class POSConnector(ABC):
    name: str = "abstract"

    @abstractmethod
    async def fetch_sales(self, *, limit: int = 50) -> list[POSSale]:
        raise NotImplementedError


class MockPOSConnector(POSConnector):
    name = "mock"

    async def fetch_sales(self, *, limit: int = 50) -> list[POSSale]:
        # Déterministe : mêmes tickets à chaque appel → idempotence démontrable.
        day = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
        sales = [
            POSSale(
                external_ref="TK-1001", sku="BAGUETTE", quantity=3, unit_price=1.1, sold_at=day
            ),
            POSSale(external_ref="TK-1002", sku="LAIT", quantity=2, unit_price=1.05, sold_at=day),
            POSSale(external_ref="TK-1003", sku="POULET", quantity=1, unit_price=8.9, sold_at=day),
        ]
        return sales[:limit]


class HttpPOSConnector(POSConnector):
    name = "http"

    async def fetch_sales(self, *, limit: int = 50) -> list[POSSale]:  # pragma: no cover
        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(settings.pos_url, params={"limit": limit})
            resp.raise_for_status()
            return [POSSale(**row) for row in resp.json()]


def get_pos_connector() -> POSConnector:
    """Retourne le connecteur caisse configuré. Sans config → mock (keyless)."""
    if settings.pos_connector.lower() == "http" and settings.pos_url:
        return HttpPOSConnector()
    if settings.pos_connector.lower() == "http":
        log.warning("pos.connector.fallback", reason="no url", to="mock")
    return MockPOSConnector()


__all__ = ["POSConnector", "POSSale", "get_pos_connector"]
