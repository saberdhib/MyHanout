"""Service de démarque (anti-gaspillage frais) : rassemble les entrées, applique
le moteur, persiste — et exécute les actions humaines (appliquer / rejeter).

Entrées par lot périssable proche de la péremption :
- quantité du lot + date de péremption (jours restants),
- vitesse de vente estimée (prévision near-term, repli historique),
- prix de vente courant + coût d'achat (historique des prix, repli marge par défaut).

Chaque suggestion persistée porte son explication + les données utilisées (audit),
et référence son `pipeline_run_id` + `model_version` (traçabilité).
"""

from __future__ import annotations

import json
from datetime import UTC, date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.tenancy import get_current_org
from app.intelligence.forecasting.service_client import get_forecast_service_client
from app.intelligence.markdown.engine import decide_markdown
from app.models.base import MarkdownStatus, PriceKind
from app.models.markdown import MarkdownSuggestion
from app.models.pricing import PriceHistory
from app.repositories.sale import SaleRepository
from app.repositories.stock import StockRepository
from app.schemas.markdown import MarkdownDecision


async def _unit_cost(session: AsyncSession, product_id: int, current_price: float) -> float:
    """Coût d'achat unitaire : dernier prix `purchase`, sinon marge par défaut."""
    row = await session.scalars(
        select(PriceHistory.price)
        .where(PriceHistory.product_id == product_id, PriceHistory.kind == PriceKind.PURCHASE)
        .order_by(PriceHistory.effective_at.desc())
        .limit(1)
    )
    cost = row.first()
    if cost is not None:
        return float(cost)
    return round(current_price * (1.0 - settings.markdown_default_margin_ratio), 2)


async def _daily_demand(
    session: AsyncSession, sale_repo: SaleRepository, product_id: int, *, horizon: int
) -> tuple[float, int]:
    """(vente/jour estimée, nb de jours d'historique) — prévision, repli historique."""
    history = await sale_repo.daily_history(product_id)
    history_days = len(history)
    try:
        client = get_forecast_service_client()
        fc = await client.predict_product(
            session, product_id, horizon_days=horizon, model_name=None
        )
        forecast_demand = float(sum(p.yhat for p in fc.points))
        daily = forecast_demand / horizon if horizon else forecast_demand
    except Exception:  # robustesse : repli sur l'historique si le forecast échoue
        daily = 0.0
    if daily <= 0 and history_days:
        daily = sum(float(y) for _, y in history) / history_days
    return round(daily, 3), history_days


async def compute_markdowns(
    session: AsyncSession,
    *,
    persist: bool = False,
    pipeline_run_id: int | None = None,
    today: date | None = None,
) -> list[MarkdownDecision]:
    """Calcule (et optionnellement persiste) les suggestions de démarque, triées par score."""
    today = today or date.today()
    horizon = settings.markdown_horizon_days
    stock_repo = StockRepository(session)
    sale_repo = SaleRepository(session)
    client = get_forecast_service_client()

    expiring = await stock_repo.list_expiring(within_days=horizon)

    if persist:
        # On remplace le jeu "suggested" précédent (garde l'historique applied/rejected).
        # DELETE ORM non filtré par le garde-fou (event SELECT only) → filtrer l'org À LA MAIN.
        org_id = get_current_org()
        if org_id is not None:
            await session.execute(
                delete(MarkdownSuggestion).where(
                    MarkdownSuggestion.organization_id == org_id,
                    MarkdownSuggestion.status == MarkdownStatus.SUGGESTED,
                )
            )

    decisions: list[MarkdownDecision] = []
    for stock in expiring:
        if stock.expiry_date is None:
            continue
        days_to_expiry = (stock.expiry_date - today).days
        if days_to_expiry < 1:
            continue  # déjà périmé → la démarque n'a plus de sens
        quantity = float(stock.quantity)
        if quantity <= 0:
            continue
        product = stock.product
        current_price = float(product.unit_price or 0.0)
        if current_price <= 0:
            continue  # pas de prix → on ne peut pas démarquer

        unit_cost = await _unit_cost(session, product.id, current_price)
        daily, history_days = await _daily_demand(session, sale_repo, product.id, horizon=horizon)

        decision = decide_markdown(
            product_id=product.id,
            quantity=quantity,
            days_to_expiry=days_to_expiry,
            avg_daily_demand=daily,
            current_price=current_price,
            unit_cost=unit_cost,
            history_days=history_days,
        )
        if decision is None:
            continue
        decisions.append(decision)

        if persist:
            session.add(
                MarkdownSuggestion(
                    product_id=product.id,
                    stock_id=stock.id,
                    pipeline_run_id=pipeline_run_id,
                    model_version=client.model_version(),
                    quantity_at_risk=decision.quantity_at_risk,
                    expiry_date=stock.expiry_date,
                    days_to_expiry=decision.days_to_expiry,
                    current_price=decision.current_price,
                    suggested_price=decision.suggested_price,
                    discount_pct=decision.discount_pct,
                    expected_units_cleared=decision.expected_units_cleared,
                    recovered_value=decision.recovered_value,
                    avoided_loss=decision.avoided_loss,
                    baseline_loss=decision.baseline_loss,
                    confidence=decision.confidence,
                    score=decision.score,
                    explanation=decision.explanation,
                    data_used=json.dumps(decision.data_used, ensure_ascii=False),
                )
            )
    if persist:
        await session.flush()

    decisions.sort(key=lambda d: d.score, reverse=True)
    return decisions


async def set_status(
    session: AsyncSession, suggestion_id: int, status: MarkdownStatus
) -> MarkdownSuggestion | None:
    """Applique/rejette une suggestion (human-in-the-loop). Le garde-fou filtre l'org."""
    sug = await session.get(MarkdownSuggestion, suggestion_id)
    if sug is None:
        return None
    sug.status = status
    # Appliquer une démarque = acter le nouveau prix de vente (trace dans l'historique).
    if status == MarkdownStatus.APPLIED:
        from datetime import datetime

        session.add(
            PriceHistory(
                product_id=sug.product_id,
                kind=PriceKind.SALE,
                price=sug.suggested_price,
                effective_at=datetime.now(UTC),
                source="markdown",
            )
        )
    await session.flush()
    return sug
