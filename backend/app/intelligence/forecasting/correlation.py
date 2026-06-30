"""Analyse de l'influence des signaux externes et des effets entre produits.

But : dire **quels facteurs sont corrélés à la demande** (météo, vacances,
carburant, foot…) et **comment les produits s'influencent** (substitution /
complémentarité), pour nourrir un meilleur forecasting — en distinguant
honnêtement **corrélation, causalité et coïncidence**.

Tout est tenant-scopé pour les ventes (via l'ORM) ; les signaux sont des données
publiques globales. Aucune dépendance lourde : corrélation de Pearson via numpy.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sale import Sale
from app.models.signal import SignalDefinition, SignalObservation
from app.schemas.insights import (
    CrossProductReport,
    FactorInsight,
    FactorReport,
    ProductRelation,
)

_CAVEAT = "Corrélation ≠ causalité : à confirmer par un test (A/B, hold-out) avant d'agir."


async def daily_sales(
    session: AsyncSession, *, product_id: int, date_from: date, date_to: date
) -> dict[date, float]:
    """Unités vendues par jour pour un produit (0 implicite les jours sans vente)."""
    rows = await session.execute(
        select(func.date(Sale.sold_at), func.sum(Sale.quantity))
        .where(
            Sale.product_id == product_id,
            func.date(Sale.sold_at) >= date_from,
            func.date(Sale.sold_at) <= date_to,
        )
        .group_by(func.date(Sale.sold_at))
    )
    out: dict[date, float] = {}
    for d, q in rows:
        out[d if isinstance(d, date) else date.fromisoformat(str(d))] = float(q or 0)
    return out


def _verdict(r: float, n: int) -> tuple[str, str]:
    """Retourne (force, verdict) à partir du coefficient et de la taille d'échantillon."""
    ar = abs(r)
    if n < 14:
        return "n/a", "données insuffisantes"
    if ar >= 0.5:
        return "forte", "corrélation probable (confirmer la causalité)"
    if ar >= 0.3:
        return "modérée", "corrélation possible"
    return "faible", "pas de lien clair (probable coïncidence)"


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    m = np.corrcoef(np.array(x), np.array(y))[0, 1]
    return None if np.isnan(m) else float(m)


async def analyze_factors(
    session: AsyncSession,
    *,
    product_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    region: str | None = None,
) -> FactorReport:
    """Classe les signaux externes par corrélation avec la demande du produit."""
    today = date.today()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=180))

    sales = await daily_sales(session, product_id=product_id, date_from=date_from, date_to=date_to)
    days = sorted(sales.keys())
    defs = list((await session.scalars(select(SignalDefinition))).all())

    factors: list[FactorInsight] = []
    for d in defs:
        obs_rows = await session.execute(
            select(SignalObservation.obs_date, SignalObservation.value).where(
                SignalObservation.signal_key == d.key,
                SignalObservation.obs_date >= date_from,
                SignalObservation.obs_date <= date_to,
            )
        )
        obs = {od: float(v) for od, v in obs_rows}
        paired = [(sales[day], obs[day]) for day in days if day in obs]
        if len(paired) < 3:
            continue
        y = [p[0] for p in paired]
        x = [p[1] for p in paired]
        r = _pearson(x, y)
        if r is None:
            continue
        strength, verdict = _verdict(r, len(paired))
        direction = "positive" if r >= 0 else "négative"
        factors.append(
            FactorInsight(
                signal_key=d.key,
                label=d.label,
                kind=d.kind.value if hasattr(d.kind, "value") else str(d.kind),
                correlation=round(r, 3),
                n=len(paired),
                direction=direction,
                strength=strength,
                verdict=verdict,
                explanation=(
                    f"{d.label} : corrélation {direction} r={r:.2f} sur {len(paired)} jours "
                    f"({verdict})."
                ),
            )
        )

    factors.sort(key=lambda f: abs(f.correlation), reverse=True)
    return FactorReport(
        product_id=product_id,
        period_from=date_from,
        period_to=date_to,
        factors=factors,
        caveat=_CAVEAT,
        explanation=(
            f"{len(factors)} facteur(s) évalué(s) sur {len(days)} jours de ventes. "
            "Classés par force de corrélation ; à utiliser comme features du forecast."
        ),
    )


async def cross_product(
    session: AsyncSession,
    *,
    product_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    top: int = 8,
) -> CrossProductReport:
    """Détecte substituts (corrélation négative) et compléments (positive) via co-ventes."""
    today = date.today()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=180))

    base = await daily_sales(session, product_id=product_id, date_from=date_from, date_to=date_to)
    days = sorted(base.keys())
    if len(days) < 14:
        return CrossProductReport(
            product_id=product_id,
            period_from=date_from,
            period_to=date_to,
            relations=[],
            caveat=_CAVEAT,
            explanation="Pas assez d'historique de ventes pour évaluer les effets entre produits.",
        )

    others = list(
        (
            await session.scalars(
                select(Sale.product_id).distinct().where(Sale.product_id != product_id)
            )
        ).all()
    )
    names: dict[int, str] = {}
    if others:
        from app.models.product import Product

        for pid, name in await session.execute(
            select(Product.id, Product.name).where(Product.id.in_(others))
        ):
            names[pid] = name

    base_vec = [base[d] for d in days]
    relations: list[ProductRelation] = []
    for pid in others:
        other = await daily_sales(session, product_id=pid, date_from=date_from, date_to=date_to)
        other_vec = [other.get(d, 0.0) for d in days]
        r = _pearson(other_vec, base_vec)
        if r is None or abs(r) < 0.3:
            continue
        strength, _ = _verdict(r, len(days))
        relation = "complement" if r > 0 else "substitute"
        relations.append(
            ProductRelation(
                product_id=pid,
                product_name=names.get(pid),
                correlation=round(r, 3),
                relation=relation,
                strength=strength,
                explanation=(
                    f"{names.get(pid, pid)} : corrélation {r:+.2f} → "
                    + (
                        "se vendent ensemble (complément)"
                        if relation == "complement"
                        else "l'un monte quand l'autre baisse (substitut)"
                    )
                ),
            )
        )

    relations.sort(key=lambda x: abs(x.correlation), reverse=True)
    return CrossProductReport(
        product_id=product_id,
        period_from=date_from,
        period_to=date_to,
        relations=relations[:top],
        caveat=_CAVEAT,
        explanation=(
            f"{len(relations)} produit(s) liés détectés (|corrélation| ≥ 0,3). "
            "Substitut = report en cas de rupture ; complément = vente jointe."
        ),
    )
