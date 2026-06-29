"""Import générique JSON (catalogue/ventes/stock) + sync DWH — tenant-scopé.

Permet d'amorcer ou de synchroniser un commerce depuis un export externe (caisse,
ERP léger, tableur). Idempotent par clés naturelles (SKU fournisseur/produit).
Toutes les écritures sont estampillées par le garde-fou tenant central.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.logging import get_logger
from app.ingestion.dwh import DwhSyncResult, get_dwh_target
from app.models.product import Product
from app.models.sale import Sale
from app.models.stock import Stock
from app.models.supplier import Supplier

log = get_logger(__name__)


class SupplierIn(BaseModel):
    name: str
    email: str | None = None
    lead_time_days: int | None = None


class ProductIn(BaseModel):
    sku: str
    name: str
    unit: str = "unit"
    unit_price: float | None = None
    category: str | None = None
    family: str | None = None  # notion de regroupement (viande, boisson…)
    perishable: bool = False
    supplier_name: str | None = None
    stock_quantity: float | None = None
    reorder_threshold: float | None = None


class SaleIn(BaseModel):
    sku: str
    quantity: float
    unit_price: float
    sold_at: datetime


class ImportPayload(BaseModel):
    suppliers: list[SupplierIn] = []
    products: list[ProductIn] = []
    sales: list[SaleIn] = []


class ImportResult(BaseModel):
    suppliers_upserted: int = 0
    products_upserted: int = 0
    stocks_upserted: int = 0
    sales_inserted: int = 0


async def _upsert_supplier(session: AsyncSession, data: SupplierIn) -> Supplier:
    existing = await session.scalar(select(Supplier).where(Supplier.name == data.name))
    sup = existing or Supplier(name=data.name)
    if data.email is not None:
        sup.email = data.email
    if data.lead_time_days is not None:
        sup.lead_time_days = data.lead_time_days
    if existing is None:
        session.add(sup)
    await session.flush()
    return sup


async def import_json(
    session: AsyncSession, *, payload: ImportPayload, user_id: int | None
) -> ImportResult:
    """Importe fournisseurs/produits/stock/ventes (idempotent par SKU)."""
    result = ImportResult()
    supplier_by_name: dict[str, Supplier] = {}

    for sup_in in payload.suppliers:
        supplier_by_name[sup_in.name] = await _upsert_supplier(session, sup_in)
        result.suppliers_upserted += 1

    for prod_in in payload.products:
        # SELECT filtré par tenant (garde-fou central) → SKU résolu dans l'org.
        product = await session.scalar(select(Product).where(Product.sku == prod_in.sku.upper()))
        if product is None:
            product = Product(sku=prod_in.sku.upper(), name=prod_in.name)
            session.add(product)
        product.name = prod_in.name
        product.unit = prod_in.unit
        product.unit_price = prod_in.unit_price
        product.category = prod_in.category
        product.family = prod_in.family
        product.perishable = prod_in.perishable
        if prod_in.supplier_name:
            sup = supplier_by_name.get(prod_in.supplier_name) or await _upsert_supplier(
                session, SupplierIn(name=prod_in.supplier_name)
            )
            supplier_by_name[prod_in.supplier_name] = sup
            product.supplier_id = sup.id
        await session.flush()
        result.products_upserted += 1

        # Historique de prix : trace le prix de vente importé (courbe d'évolution).
        if prod_in.unit_price is not None:
            from app.models.base import PriceKind
            from app.services.price_service import record_price

            await record_price(
                session,
                product_id=product.id,
                kind=PriceKind.SALE,
                price=prod_in.unit_price,
                source="import",
            )

        if prod_in.stock_quantity is not None:
            stock = await session.scalar(select(Stock).where(Stock.product_id == product.id))
            if stock is None:
                stock = Stock(product_id=product.id)
                session.add(stock)
            stock.quantity = prod_in.stock_quantity
            if prod_in.reorder_threshold is not None:
                stock.reorder_threshold = prod_in.reorder_threshold
            result.stocks_upserted += 1

    for sale_in in payload.sales:
        product = await session.scalar(select(Product).where(Product.sku == sale_in.sku.upper()))
        if product is None:
            continue  # vente sans produit connu : ignorée (traçable via les compteurs)
        session.add(
            Sale(
                product_id=product.id,
                quantity=sale_in.quantity,
                unit_price=sale_in.unit_price,
                total=sale_in.quantity * sale_in.unit_price,
                sold_at=sale_in.sold_at,
            )
        )
        result.sales_inserted += 1

    await session.flush()
    await record_audit(
        session,
        action="data.import_json",
        user_id=user_id,
        resource="import",
        detail=(
            f"suppliers={result.suppliers_upserted} products={result.products_upserted} "
            f"stocks={result.stocks_upserted} sales={result.sales_inserted}"
        ),
    )
    log.info("data.import_json", **result.model_dump())
    return result


async def sync_to_dwh(
    session: AsyncSession, *, organization_id: int, user_id: int | None
) -> DwhSyncResult:
    """Exporte un snapshot (catalogue + stock + ventes) vers l'entrepôt configuré."""
    products = list((await session.scalars(select(Product))).all())
    stocks = list((await session.scalars(select(Stock))).all())
    sales = list((await session.scalars(select(Sale))).all())
    snapshot = {
        "generated_at": datetime.now(UTC).isoformat(),
        "products": [{"sku": p.sku, "name": p.name, "unit": p.unit} for p in products],
        "stocks": [{"product_id": s.product_id, "quantity": float(s.quantity)} for s in stocks],
        "sales": [
            {
                "product_id": s.product_id,
                "quantity": float(s.quantity),
                "total": float(s.total),
                "sold_at": s.sold_at.isoformat(),
            }
            for s in sales
        ],
    }
    result = await get_dwh_target().push(organization_id=organization_id, snapshot=snapshot)
    await record_audit(
        session,
        action="data.dwh_sync",
        user_id=user_id,
        resource="dwh",
        detail=f"target={result.target} rows={result.rows}",
    )
    log.info("data.dwh_sync", target=result.target, rows=result.rows)
    return result
