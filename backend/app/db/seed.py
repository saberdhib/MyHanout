"""Chargement des données de démonstration.

Usage : `python -m app.db.seed` (ou `make seed`).
Idempotent : ne réinsère pas si des produits existent déjà.
"""

from __future__ import annotations

import asyncio
import csv
import json
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import (
    Invoice,
    InvoiceLine,
    Product,
    Role,
    Sale,
    Stock,
    Supplier,
    User,
)
from app.models.base import InvoiceStatus, OcrStatus

log = get_logger(__name__)


def _seed_dir() -> Path:
    """Résout le répertoire des seeds (docker /data/seeds ou repo-relatif)."""
    candidate = Path(settings.seed_dir)
    if candidate.exists():
        return candidate
    # Fallback : <repo>/data/seeds depuis backend/app/db/seed.py
    return Path(__file__).resolve().parents[3] / "data" / "seeds"


DEFAULT_ROLES = [
    ("owner", "Propriétaire — accès complet", "*"),
    ("manager", "Gérant — gestion stocks/commandes", "stocks,orders,invoices,forecasts"),
    ("staff", "Employé — lecture + saisie", "stocks,invoices"),
    ("viewer", "Lecture seule", "read"),
]


async def seed() -> None:
    configure_logging()
    seeds = _seed_dir()
    log.info("seed.start", seed_dir=str(seeds))

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(func.count()).select_from(Product))
        if existing:
            log.info("seed.skip", reason="data already present", products=existing)
            return

        # --- Rôles + utilisateur admin ---
        roles: dict[str, Role] = {}
        for name, desc, perms in DEFAULT_ROLES:
            role = Role(name=name, description=desc, permissions=perms)
            session.add(role)
            roles[name] = role
        # Comptes de démo (mots de passe via env, cf. .env.example).
        session.add(
            User(
                email="admin@myhanout.example",
                full_name="Admin Démo",
                hashed_password=hash_password(settings.seed_admin_password),
                role=roles["owner"],
            )
        )
        session.add(
            User(
                email="merchant@myhanout.example",
                full_name="Commerçant Démo",
                hashed_password=hash_password(settings.seed_merchant_password),
                role=roles["manager"],
            )
        )

        # --- Fournisseurs ---
        suppliers: dict[str, Supplier] = {}
        with open(seeds / "suppliers.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                s = Supplier(
                    name=row["name"],
                    contact_name=row["contact_name"],
                    email=row["email"],
                    phone=row["phone"],
                    payment_terms_days=int(row["payment_terms_days"]),
                )
                session.add(s)
                suppliers[s.name] = s

        # --- Produits + stock initial ---
        products: dict[str, Product] = {}
        with open(seeds / "products.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                p = Product(
                    sku=row["sku"],
                    name=row["name"],
                    category=row["category"],
                    unit=row["unit"],
                    unit_price=float(row["unit_price"]),
                    perishable=row["perishable"].lower() == "true",
                    shelf_life_days=int(row["shelf_life_days"]) if row["shelf_life_days"] else None,
                    supplier=suppliers.get(row["supplier_name"]),
                )
                session.add(p)
                products[p.sku] = p
                # Stock initial arbitraire + seuil de réassort.
                session.add(
                    Stock(
                        product=p,
                        quantity=20,
                        reorder_threshold=10,
                        expiry_date=None,
                    )
                )

        await session.flush()  # garantit les PK pour les FK ci-dessous

        # --- Ventes ---
        sales_count = 0
        with open(seeds / "sales.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                product = products.get(row["product_sku"])
                if not product:
                    continue
                session.add(
                    Sale(
                        product_id=product.id,
                        quantity=float(row["quantity"]),
                        unit_price=float(row["unit_price"]),
                        total=float(row["total"]),
                        sold_at=datetime.fromisoformat(row["sold_at"]),
                    )
                )
                sales_count += 1

        # --- Factures ---
        with open(seeds / "invoices.json", encoding="utf-8") as f:
            invoices_data = json.load(f)
        for inv in invoices_data:
            invoice = Invoice(
                number=inv["number"],
                supplier=suppliers.get(inv["supplier_name"]),
                issue_date=date.fromisoformat(inv["issue_date"]),
                due_date=date.fromisoformat(inv["due_date"]),
                currency=inv.get("currency", "EUR"),
                status=InvoiceStatus(inv.get("status", "pending")),
                ocr_status=OcrStatus(inv.get("ocr_status", "done")),
                source_uri=inv.get("source_uri"),
            )
            total = 0.0
            for line in inv["lines"]:
                product = products.get(line["product_sku"])
                line_total = line["quantity"] * line["unit_price"]
                total += line_total
                invoice.lines.append(
                    InvoiceLine(
                        product_id=product.id if product else None,
                        description=line["description"],
                        quantity=line["quantity"],
                        unit_price=line["unit_price"],
                        line_total=line_total,
                    )
                )
            invoice.total_amount = total
            session.add(invoice)

        await session.commit()
        log.info(
            "seed.done",
            suppliers=len(suppliers),
            products=len(products),
            sales=sales_count,
            invoices=len(invoices_data),
        )


if __name__ == "__main__":
    asyncio.run(seed())
