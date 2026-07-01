"""Tests contrôles : 3-way match factures + démarque inconnue."""

from __future__ import annotations

import asyncio
import datetime
import uuid
from datetime import UTC, date, timedelta

from sqlalchemy import select

import app.models as m
from app.core.tenancy import tenant_context
from app.models.base import PriceKind
from tests.conftest import TestSession


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _seed_controls(slug: str = "org-a") -> dict[str, int]:
    """Un produit avec : hausse de prix facturée, commande moins chère, et stock manquant."""
    async with TestSession() as s:
        org = (await s.scalars(select(m.Organization).where(m.Organization.slug == slug))).first()
        assert org is not None
        suffix = uuid.uuid4().hex[:8]
        with tenant_context(org.id):
            sup = m.Supplier(name=f"Fournisseur ctl {suffix}", payment_terms_days=30)
            prod = m.Product(sku=f"CTL-{suffix}", name="Huile contrôle", unit="unit", unit_price=10)
            s.add_all([sup, prod])
            await s.flush()

            # Historique : coût d'achat connu à 6 € (avant la facture).
            s.add(
                m.PriceHistory(
                    product_id=prod.id,
                    kind=PriceKind.PURCHASE,
                    price=6,
                    effective_at=datetime.datetime(2026, 5, 1, tzinfo=UTC),
                    source="test",
                )
            )
            # Commande fournisseur à 6 € pour 10 unités.
            order = m.Order(supplier_id=sup.id, total_amount=60)
            order.lines.append(m.OrderLine(product_id=prod.id, quantity=10, unit_price=6))
            s.add(order)
            # Facture : 12 unités à 8 € (dérive prix + quantité > commande).
            inv = m.Invoice(
                number=f"CTL-{suffix}",
                supplier=sup,
                currency="EUR",
                issue_date=date.today(),
                total_amount=96,
            )
            inv.lines.append(
                m.InvoiceLine(
                    product_id=prod.id,
                    description="Huile",
                    quantity=12,
                    unit_price=8,
                    line_total=96,
                )
            )
            s.add(inv)

            # Démarque inconnue : snapshot 20, +12 achetés, -5 vendus → attendu 27, réel 20.
            s.add(
                m.InventorySnapshot(
                    product_id=prod.id,
                    snapshot_date=date.today() - timedelta(days=10),
                    quantity=20,
                )
            )
            s.add(m.Stock(product_id=prod.id, quantity=20, reorder_threshold=5))
            for _ in range(5):
                s.add(
                    m.Sale(
                        product_id=prod.id,
                        quantity=1,
                        unit_price=10,
                        total=10,
                        sold_at=datetime.datetime.now(UTC),
                    )
                )
            await s.flush()  # flush DANS le tenant_context → estampille organization_id
        await s.commit()
        return {"product_id": prod.id, "invoice_id": inv.id}


def test_invoice_controls_detect_price_and_qty(client):
    ids = _run(_seed_controls())
    report = client.get("/api/v1/controls/invoices").json()
    mine = [f for f in report["findings"] if f["product_id"] == ids["product_id"]]
    kinds = {f["kind"] for f in mine}
    assert "price_drift" in kinds  # 8 € facturé vs 6 € connu
    assert "price_vs_order" in kinds  # 8 € facturé vs 6 € commandé
    assert "qty_vs_order" in kinds  # 12 facturés vs 10 commandés
    assert all(f["overcharge"] > 0 and f["explanation"] for f in mine)
    assert report["total_overcharge"] > 0


def test_shrinkage_detects_missing_units(client):
    ids = _run(_seed_controls())
    report = client.get("/api/v1/controls/shrinkage").json()
    mine = next((i for i in report["items"] if i["product_id"] == ids["product_id"]), None)
    assert mine is not None, "l'écart de stock doit être détecté"
    # attendu = 20 + 12 − 5 = 27 ; réel = 20 → 7 manquants.
    assert mine["expected_stock"] == 27
    assert mine["actual_stock"] == 20
    assert mine["missing_units"] == 7
    assert mine["estimated_loss"] > 0
    assert "manquant" in mine["explanation"]
