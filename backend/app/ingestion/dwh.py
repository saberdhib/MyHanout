"""Synchronisation vers un entrepôt de données (DWH) — abstraction + mock keyless.

Le mock journalise localement (aucune donnée ne quitte le système). Une cible
HTTP réelle (POST d'un snapshot JSON) se branche derrière la même interface,
activée par env (`DWH_TARGET=http`, `DWH_URL=...`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class DwhSyncResult(BaseModel):
    target: str
    rows: int
    detail: str | None = None


class DwhSyncTarget(ABC):
    name: str = "abstract"

    @abstractmethod
    async def push(self, *, organization_id: int, snapshot: dict) -> DwhSyncResult:
        """Pousse un snapshot (dict sérialisable) vers l'entrepôt."""
        raise NotImplementedError


class MockDwhTarget(DwhSyncTarget):
    name = "mock"

    async def push(self, *, organization_id: int, snapshot: dict) -> DwhSyncResult:
        rows = sum(len(v) for v in snapshot.values() if isinstance(v, list))
        log.info("dwh.mock.push", org=organization_id, rows=rows, tables=list(snapshot))
        return DwhSyncResult(target=self.name, rows=rows, detail="snapshot journalisé (mock)")


class HttpDwhTarget(DwhSyncTarget):
    name = "http"

    async def push(  # pragma: no cover - réseau
        self, *, organization_id: int, snapshot: dict
    ) -> DwhSyncResult:
        import httpx

        rows = sum(len(v) for v in snapshot.values() if isinstance(v, list))
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                settings.dwh_url,
                json={"organization_id": organization_id, "snapshot": snapshot},
            )
            resp.raise_for_status()
        log.info("dwh.http.push", org=organization_id, rows=rows, url=settings.dwh_url)
        return DwhSyncResult(target=self.name, rows=rows, detail=f"POST {settings.dwh_url}")


def get_dwh_target() -> DwhSyncTarget:
    """Retourne la cible DWH configurée. Sans URL → mock (keyless)."""
    if settings.dwh_target.lower() == "http" and settings.dwh_url:
        return HttpDwhTarget()
    if settings.dwh_target.lower() == "http":
        log.warning("dwh.target.fallback", reason="no url", to="mock")
    return MockDwhTarget()
