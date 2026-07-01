"""Contrôles explicables : 3-way match factures + démarque inconnue.

Deux analyses « posture conseil », calculées à la volée sur les données existantes
(aucune table dédiée) :

1. **Contrôle factures (3-way match léger)** — pour chaque ligne de facture liée à
   un produit : le prix facturé est comparé au dernier coût d'achat connu (dérive)
   et, si une commande du même fournisseur contient le produit, au prix/quantité
   commandés. Tout écart au-delà de la tolérance est signalé avec son coût en €.

2. **Démarque inconnue (vol / casse / erreurs de saisie)** — par produit :
   stock attendu = inventaire de référence (snapshot) + achats − ventes ;
   l'écart avec le stock réel, valorisé au coût d'achat, est la perte invisible.

Le garde-fou tenant filtre Invoice/Order/Sale/Stock/Snapshot ; les lignes
(InvoiceLine/OrderLine) sont atteintes via leur parent tenant (jointure).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.base import PriceKind
from app.models.inventory import InventorySnapshot
from app.models.invoice import Invoice, InvoiceLine
from app.models.order import Order, OrderLine
from app.models.pricing import PriceHistory
from app.models.product import Product
from app.models.sale import Sale
from app.models.stock import Stock
from app.schemas.control import (
    InvoiceControlReport,
    InvoiceFinding,
    ShrinkageItem,
    ShrinkageReport,
)


async def _names(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = await session.execute(select(Product.id, Product.name).where(Product.id.in_(ids)))
    return {r[0]: r[1] for r in rows}


async def _last_purchase_price(
    session: AsyncSession, product_id: int, before: date | None
) -> float | None:
    stmt = (
        select(PriceHistory.price)
        .where(PriceHistory.product_id == product_id, PriceHistory.kind == PriceKind.PURCHASE)
        .order_by(PriceHistory.effective_at.desc())
        .limit(1)
    )
    if before is not None:
        stmt = stmt.where(func.date(PriceHistory.effective_at) < before)
    price = (await session.scalars(stmt)).first()
    return float(price) if price is not None else None


async def invoice_controls(session: AsyncSession, *, limit: int = 50) -> InvoiceControlReport:
    """3-way match léger : facture ↔ dernier coût connu ↔ commande fournisseur."""
    tol = settings.control_price_tolerance_pct / 100.0
    invoices = list(
        (
            await session.scalars(
                select(Invoice)
                .options(selectinload(Invoice.lines), selectinload(Invoice.supplier))
                .order_by(Invoice.id.desc())
                .limit(limit)
            )
        ).all()
    )

    # Prix commandés par (supplier_id, product_id) — dernières commandes d'abord.
    order_rows = await session.execute(
        select(Order.supplier_id, OrderLine.product_id, OrderLine.quantity, OrderLine.unit_price)
        .join(OrderLine, OrderLine.order_id == Order.id)
        .order_by(Order.id.desc())
    )
    ordered: dict[tuple[int | None, int], tuple[float, float]] = {}
    for supplier_id, pid, qty, price in order_rows:
        ordered.setdefault((supplier_id, pid), (float(qty), float(price)))

    findings: list[InvoiceFinding] = []
    pids: set[int] = set()
    for inv in invoices:
        supplier_name = inv.supplier.name if inv.supplier else None
        for line in inv.lines:
            if line.product_id is None or float(line.quantity) <= 0:
                continue
            pids.add(line.product_id)
            billed = float(line.unit_price)
            qty = float(line.quantity)

            # 1) Dérive vs dernier coût d'achat connu AVANT la facture.
            prior = await _last_purchase_price(session, line.product_id, inv.issue_date)
            if prior and billed > prior * (1 + tol):
                findings.append(
                    InvoiceFinding(
                        invoice_id=inv.id,
                        invoice_number=inv.number,
                        supplier_name=supplier_name,
                        product_id=line.product_id,
                        kind="price_drift",
                        expected=round(prior, 2),
                        observed=round(billed, 2),
                        overcharge=round((billed - prior) * qty, 2),
                        explanation=(
                            f"Facture {inv.number} : facturé {billed:.2f} € vs dernier coût "
                            f"connu {prior:.2f} € ({(billed - prior) / prior:+.0%}) "
                            f"→ ~{(billed - prior) * qty:.2f} € d'écart sur {qty:g} unité(s)."
                        ),
                    )
                )

            # 2) Écart vs commande du même fournisseur (si trouvée).
            key = (inv.supplier_id, line.product_id)
            if key in ordered:
                o_qty, o_price = ordered[key]
                if o_price > 0 and billed > o_price * (1 + tol):
                    findings.append(
                        InvoiceFinding(
                            invoice_id=inv.id,
                            invoice_number=inv.number,
                            supplier_name=supplier_name,
                            product_id=line.product_id,
                            kind="price_vs_order",
                            expected=round(o_price, 2),
                            observed=round(billed, 2),
                            overcharge=round((billed - o_price) * qty, 2),
                            explanation=(
                                f"Facture {inv.number} : facturé {billed:.2f} € alors que la "
                                f"commande prévoyait {o_price:.2f} € "
                                f"→ ~{(billed - o_price) * qty:.2f} € payés en trop."
                            ),
                        )
                    )
                if qty > o_qty:
                    findings.append(
                        InvoiceFinding(
                            invoice_id=inv.id,
                            invoice_number=inv.number,
                            supplier_name=supplier_name,
                            product_id=line.product_id,
                            kind="qty_vs_order",
                            expected=o_qty,
                            observed=qty,
                            overcharge=round((qty - o_qty) * billed, 2),
                            explanation=(
                                f"Facture {inv.number} : {qty:g} facturé(s) pour {o_qty:g} "
                                f"commandé(s) → vérifier la livraison "
                                f"(~{(qty - o_qty) * billed:.2f} €)."
                            ),
                        )
                    )

    names = await _names(session, pids)
    for f in findings:
        f.product_name = names.get(f.product_id)
    findings.sort(key=lambda f: f.overcharge, reverse=True)
    total = round(sum(f.overcharge for f in findings), 2)
    return InvoiceControlReport(
        findings=findings,
        total_overcharge=total,
        invoices_checked=len(invoices),
        explanation=(
            f"{len(invoices)} facture(s) contrôlée(s), {len(findings)} écart(s) détecté(s) "
            f"(tolérance {settings.control_price_tolerance_pct:.0f}%) — "
            f"~{total:.0f} € à vérifier avec vos fournisseurs."
        ),
    )


async def shrinkage_report(session: AsyncSession, *, today: date | None = None) -> ShrinkageReport:
    """Démarque inconnue : stock attendu (référence + achats − ventes) vs stock réel."""
    today = today or date.today()

    # Référence = plus ancien snapshot par produit (posé par le cycle quotidien).
    snaps = await session.execute(
        select(
            InventorySnapshot.product_id,
            InventorySnapshot.snapshot_date,
            InventorySnapshot.quantity,
        ).order_by(InventorySnapshot.snapshot_date.asc())
    )
    baseline: dict[int, tuple[date, float]] = {}
    for pid, sdate, qty in snaps:
        baseline.setdefault(pid, (sdate, float(qty)))

    items: list[ShrinkageItem] = []
    names = await _names(session, set(baseline.keys()))
    for pid, (bdate, bqty) in baseline.items():
        purchased = float(
            (
                await session.execute(
                    select(func.sum(InvoiceLine.quantity))
                    .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
                    .where(InvoiceLine.product_id == pid, Invoice.issue_date >= bdate)
                )
            ).scalar()
            or 0.0
        )
        sold = float(
            (
                await session.execute(
                    select(func.sum(Sale.quantity)).where(
                        Sale.product_id == pid, func.date(Sale.sold_at) >= bdate
                    )
                )
            ).scalar()
            or 0.0
        )
        actual = float(
            (
                await session.execute(
                    select(func.sum(Stock.quantity)).where(Stock.product_id == pid)
                )
            ).scalar()
            or 0.0
        )
        expected = bqty + purchased - sold
        missing = round(expected - actual, 2)
        if missing < settings.shrinkage_min_units:
            continue
        cost = await _last_purchase_price(session, pid, None)
        if cost is None:
            unit_price = (
                await session.execute(select(Product.unit_price).where(Product.id == pid))
            ).scalar()
            cost = float(unit_price or 0.0) * (1 - settings.markdown_default_margin_ratio)
        loss = round(missing * cost, 2)
        items.append(
            ShrinkageItem(
                product_id=pid,
                product_name=names.get(pid),
                baseline_date=bdate.isoformat(),
                baseline_qty=round(bqty, 2),
                purchased_since=round(purchased, 2),
                sold_since=round(sold, 2),
                expected_stock=round(expected, 2),
                actual_stock=round(actual, 2),
                missing_units=missing,
                estimated_loss=loss,
                explanation=(
                    f"Depuis le {bdate.isoformat()} : {bqty:g} en réserve + {purchased:g} "
                    f"acheté(s) − {sold:g} vendu(s) = {expected:g} attendu, or il en reste "
                    f"{actual:g} → {missing:g} manquant(s) (~{loss:.0f} €). "
                    "Piste : casse, vol ou erreur de saisie."
                ),
            )
        )

    items.sort(key=lambda i: i.estimated_loss, reverse=True)
    total = round(sum(i.estimated_loss for i in items), 2)
    return ShrinkageReport(
        items=items,
        total_loss=total,
        products_checked=len(baseline),
        explanation=(
            f"{len(baseline)} produit(s) contrôlé(s) depuis leur inventaire de référence : "
            f"{len(items)} écart(s) inexpliqué(s), ~{total:.0f} € de pertes invisibles."
        ),
    )
