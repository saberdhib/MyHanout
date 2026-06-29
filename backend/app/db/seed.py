"""Chargement des données de démonstration (multi-tenant).

Usage : `python -m app.db.seed` (ou `make seed`).
Idempotent : ne réinsère pas si une organisation « demo » existe déjà.
Crée une org de démo (owner + comptable) + produits/fournisseurs/ventes/factures.
"""

from __future__ import annotations

import asyncio
import csv
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.db.session import AsyncSessionLocal
from app.models import (
    Customer,
    Invoice,
    InvoiceLine,
    Membership,
    MembershipRole,
    Organization,
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
    return Path(__file__).resolve().parents[3] / "data" / "seeds"


DEFAULT_ROLES = [
    ("owner", "Propriétaire — accès complet", "*"),
    ("manager", "Gérant — gestion stocks/commandes", "stocks,orders,invoices,forecasts"),
    ("staff", "Employé — lecture + saisie", "stocks,invoices"),
    ("viewer", "Lecture seule", "read"),
]


async def _seed_business_data(session: AsyncSession, seeds: Path) -> None:
    """Insère fournisseurs/produits/stocks/ventes/factures (org courante stampée)."""
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
            session.add(Stock(product=p, quantity=20, reorder_threshold=10, expiry_date=None))

    await session.flush()

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

    # Démo couche finance : charges non-marchandise à classer (OPEX/CAPEX).
    energy_supplier = Supplier(name="EDF Énergie", payment_terms_days=15)
    telecom_supplier = Supplier(name="Orange Pro", payment_terms_days=30)
    session.add_all([energy_supplier, telecom_supplier])
    await session.flush()
    expense_invoices = [
        ("FAC-ELEC-06", energy_supplier, "Électricité juin", 180.0, False),
        ("FAC-TEL-06", telecom_supplier, "Abonnement fibre + mobile", 49.9, True),
        ("FAC-FRIGO-01", None, "Vitrine réfrigérée (matériel)", 1290.0, False),
    ]
    for number, supplier, label, amount, paid in expense_invoices:
        inv = Invoice(
            number=number,
            supplier=supplier,
            issue_date=date.today() - timedelta(days=5),
            due_date=date.today() + timedelta(days=10),
            currency="EUR",
            status=InvoiceStatus.PAID if paid else InvoiceStatus.PENDING,
            ocr_status=OcrStatus.DONE,
            total_amount=amount,
            paid=paid,
            paid_at=datetime.now(UTC) if paid else None,
        )
        inv.lines.append(
            InvoiceLine(description=label, quantity=1, unit_price=amount, line_total=amount)
        )
        session.add(inv)

    # Démo chaîne du froid : 2 frigos + 1 congélateur (un capteur en dérive).
    from app.models.base import EquipmentKind
    from app.models.equipment import Equipment

    session.add_all(
        [
            Equipment(
                name="Frigo vitrine",
                kind=EquipmentKind.FRIDGE,
                location="Magasin",
                min_temp_c=0,
                max_temp_c=4,
                sensor_external_id="sensor-fridge-1",
            ),
            Equipment(
                name="Frigo réserve (à surveiller)",
                kind=EquipmentKind.FRIDGE,
                location="Réserve",
                min_temp_c=0,
                max_temp_c=4,
                sensor_external_id="sensor-fridge-hot",  # mock → dérive (démo)
            ),
            Equipment(
                name="Congélateur",
                kind=EquipmentKind.FREEZER,
                location="Réserve",
                min_temp_c=-25,
                max_temp_c=-18,
                sensor_external_id="sensor-freezer-1",
            ),
        ]
    )

    # Démo : un périssable en fin de vie (déclenche la promo flash) + clients opt-in.
    soon = date.today() + timedelta(days=2)
    for product in products.values():
        if product.perishable:
            session.add(Stock(product=product, quantity=4, reorder_threshold=10, expiry_date=soon))
            break
    session.add_all(
        [
            Customer(
                name="Amina",
                phone="+212600000010",
                consent_opt_in=True,
                consent_at=datetime.now(UTC),
            ),
            Customer(name="Hassan", phone="+212600000011", consent_opt_in=False),
        ]
    )

    log.info("seed.business", suppliers=len(suppliers), products=len(products), sales=sales_count)


async def seed() -> None:
    configure_logging()
    seeds = _seed_dir()
    log.info("seed.start", seed_dir=str(seeds))

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(func.count()).select_from(Organization).where(Organization.slug == "demo")
        )
        if existing:
            log.info("seed.skip", reason="org demo already present")
            return

        # Référentiel global des catégories de charges (idempotent, non tenant).
        from app.intelligence.finance.categories import seed_expense_categories

        await seed_expense_categories(session)

        # Organisation de démo (tenant).
        org = Organization(name="Commerce Démo", slug="demo", business_type="epicerie")
        session.add(org)

        # Rôles legacy (vestigiaux) + utilisateurs + memberships.
        roles = {
            name: Role(name=name, description=desc, permissions=perms)
            for name, desc, perms in DEFAULT_ROLES
        }
        session.add_all(list(roles.values()))

        owner_user = User(
            email="admin@myhanout.example",
            full_name="Admin Démo",
            hashed_password=hash_password(settings.seed_admin_password),
            role=roles["owner"],
        )
        accountant_user = User(
            email="accountant@myhanout.example",
            full_name="Comptable Démo",
            hashed_password=hash_password(settings.seed_merchant_password),
            role=roles["viewer"],
        )
        session.add_all([owner_user, accountant_user])
        await session.flush()

        session.add_all(
            [
                Membership(
                    user_id=owner_user.id, organization_id=org.id, role=MembershipRole.OWNER
                ),
                Membership(
                    user_id=accountant_user.id,
                    organization_id=org.id,
                    role=MembershipRole.ACCOUNTANT,
                ),
            ]
        )

        # Estampillage automatique des données métier sur l'org démo.
        # Le commit DOIT rester dans le contexte pour stamper les inserts différés.
        with tenant_context(org.id):
            await _seed_business_data(session, seeds)
            await session.commit()
        log.info("seed.done", organization=org.slug)


if __name__ == "__main__":
    asyncio.run(seed())
