"""Frontière de service pour le forecasting (Brique 2).

Le forecast peut tourner **dans l'API** (défaut keyless, `inprocess`) ou dans un
**service ML isolé** (`ml-service/`, scalable indépendamment) appelé en HTTP.
L'abstraction `ForecastServiceClient` rend ce choix transparent ; si le service
HTTP est configuré mais injoignable → **fallback in-process** (on ne casse rien).

Chaque prévision porte une `model_version` (traçabilité MLOps).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.forecasting import ForecastResult, get_forecast_model
from app.intelligence.forecasting.base import HistoryPoint
from app.repositories.sale import SaleRepository

log = get_logger(__name__)


class ForecastServiceClient(ABC):
    name: str = "abstract"

    @abstractmethod
    async def predict_product(
        self,
        session: AsyncSession,
        product_id: int,
        *,
        horizon_days: int,
        model_name: str | None = None,
    ) -> ForecastResult: ...

    def model_version(self) -> str:
        return settings.model_version


class InProcessForecastClient(ForecastServiceClient):
    """Exécute le modèle dans le process de l'API (défaut, keyless)."""

    name = "inprocess"

    async def predict_product(
        self, session, product_id, *, horizon_days, model_name=None
    ) -> ForecastResult:
        from app.services.forecast_service import forecast_product

        return await forecast_product(
            session, product_id, horizon_days=horizon_days, model_name=model_name
        )


class HttpForecastClient(ForecastServiceClient):
    """Appelle le service ML isolé (ml-service/). Fallback in-process si KO."""

    name = "http"

    async def predict_product(
        self, session, product_id, *, horizon_days, model_name=None
    ) -> ForecastResult:  # pragma: no cover - réseau (testé via mock/in-process)
        import httpx

        repo = SaleRepository(session)
        rows = await repo.daily_history(product_id)
        history = [
            {
                "ds": (ds if isinstance(ds, date) else date.fromisoformat(str(ds))).isoformat(),
                "y": y,
            }
            for ds, y in rows
        ]
        try:
            headers = (
                {"X-Internal-Key": settings.ml_internal_key} if settings.ml_internal_key else {}
            )
            async with httpx.AsyncClient(timeout=30) as http:
                resp = await http.post(
                    f"{settings.ml_service_url}/predict",
                    headers=headers,
                    json={
                        "product_id": product_id,
                        "horizon_days": horizon_days,
                        "model": model_name or settings.forecast_model,
                        "history": history,
                    },
                )
                resp.raise_for_status()
                return ForecastResult.model_validate(resp.json())
        except Exception as exc:  # service down → on ne casse pas la demande
            log.warning("forecast_service.fallback", reason=str(exc), to="inprocess")
            model = get_forecast_model(model_name)
            return model.predict(
                [HistoryPoint(ds=date.fromisoformat(p["ds"]), y=p["y"]) for p in history],
                horizon_days=horizon_days,
                product_id=product_id,
            )


def get_forecast_service_client() -> ForecastServiceClient:
    """Client configuré. Sans service HTTP → in-process (keyless)."""
    if settings.forecast_service_client.lower() == "http":
        return HttpForecastClient()
    return InProcessForecastClient()
