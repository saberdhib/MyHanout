"""Mode démo blindé : un jeu de données ultra-réaliste pour une boucherie fictive.

But : charger d'**une seule commande** un commerce complet sur ~3 mois pour qu'une
démonstration devant un commerçant **allume toutes les pages** (dashboard, prévisions,
stocks/alertes, démarque/impact, échéancier/trésorerie, fidélité, réservations,
production, chaîne du froid, briefing du jour) sans aucune saisie manuelle.

Usage : `python -m app.db.seed_demo` (ou `make seed-demo`).
Idempotent : ne réinsère pas si l'organisation « boucherie-demo » existe déjà.

Toutes les données sont **fictives** (RGPD) et déterministes (pas d'aléa réseau).
Le commit reste DANS le `tenant_context` pour estamper les inserts différés (cf. CLAUDE.md).
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, date, datetime, timedelta

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
    Recipe,
    RecipeItem,
    Role,
    Sale,
    Stock,
    Supplier,
    User,
)
from app.models.base import EquipmentKind, InvoiceStatus, MarkdownStatus, OcrStatus
from app.models.equipment import Equipment
from app.models.loyalty import LoyaltyAccount, LoyaltyTransaction, LoyaltyTxnKind
from app.models.markdown import MarkdownSuggestion
from app.models.reservation import Reservation, ReservationLine, ReservationStatus

log = get_logger(__name__)

DEMO_SLUG = "boucherie-demo"
DEMO_OWNER_EMAIL = "boucher@myhanout.example"
# product.sku est unique GLOBALEMENT (pas tenant-scopé) → on préfixe pour ne pas
# collisionner avec un autre catalogue seedé (démo principale, tests).
_SKU_PREFIX = "BCHD-"

# --- Catalogue boucherie (prix EUR, coût ≈ 72 % du prix de vente) ------------
# (sku, nom, unité, prix, périssable, dlc_jours, demande_base_jour)
_PRODUCTS: list[tuple[str, str, str, float, bool, int | None, float]] = [
    ("BOEUF-BAVETTE", "Bavette de bœuf", "kg", 18.90, True, 4, 6.0),
    ("BOEUF-ENTRECOTE", "Entrecôte de bœuf", "kg", 26.50, True, 4, 4.0),
    ("BOEUF-HACHE", "Viande hachée de bœuf", "kg", 14.90, True, 2, 9.0),
    ("BOEUF-BROCHETTE", "Brochettes de bœuf", "kg", 17.90, True, 2, 5.0),
    ("VEAU-ESCALOPE", "Escalope de veau", "kg", 24.00, True, 3, 3.0),
    ("AGNEAU-COTES", "Côtelettes d'agneau", "kg", 22.00, True, 4, 4.0),
    ("AGNEAU-GIGOT", "Gigot d'agneau", "kg", 19.50, True, 5, 2.0),
    ("POULET-ENTIER", "Poulet fermier entier", "unit", 9.90, True, 5, 8.0),
    ("POULET-ESCALOPE", "Escalope de poulet", "kg", 12.90, True, 3, 7.0),
    ("DINDE-ESCALOPE", "Escalope de dinde", "kg", 11.50, True, 3, 3.0),
    ("MERGUEZ", "Merguez maison", "kg", 13.90, True, 3, 6.0),
    ("SAUCISSE-VOL", "Saucisse de volaille", "kg", 12.50, True, 3, 4.0),
    ("FOIE-VOLAILLE", "Foies de volaille", "kg", 8.90, True, 2, 2.0),
    ("EPICE-MERGUEZ", "Mélange épices merguez", "kg", 22.00, False, None, 0.3),
]

# Saisonnalité hebdo d'une boucherie de quartier : fermée le lundi, pic week-end.
_WEEKDAY_MULT = {0: 0.0, 1: 0.7, 2: 0.8, 3: 0.9, 4: 1.3, 5: 1.7, 6: 1.1}

_HISTORY_DAYS = 90


async def _get_or_create_owner_role(session: AsyncSession) -> Role:
    """Rôle legacy « owner » (global, non tenant) — partagé avec le seed principal."""
    role = await session.scalar(select(Role).where(Role.name == "owner"))
    if role is None:
        role = Role(name="owner", description="Propriétaire — accès complet", permissions="*")
        session.add(role)
        await session.flush()
    return role


def _demand(base: float, day: date, day_index: int) -> float:
    """Demande quotidienne déterministe : saisonnalité hebdo + légère tendance + vague."""
    mult = _WEEKDAY_MULT[day.weekday()]
    if mult == 0.0:
        return 0.0
    trend = 1.0 + 0.0015 * day_index  # croissance douce sur 3 mois
    wave = 1.0 + 0.08 * math.sin(day_index / 6.0)  # micro-variations réalistes
    return round(base * mult * trend * wave, 2)


async def _seed_boucherie(session: AsyncSession, org: Organization, owner: User) -> None:
    """Insère tout le métier de la boucherie (org courante estampée par le garde-fou)."""
    today = date.today()

    # --- Fournisseurs -------------------------------------------------------
    abattoir = Supplier(
        name="Abattoir Régional",
        contact_name="M. Bernard",
        email="commande@abattoir-regional.example",
        phone="+33123456789",
        payment_terms_days=30,
        lead_time_days=2,
    )
    volailler = Supplier(
        name="Volailles du Terroir",
        contact_name="Mme Petit",
        email="ventes@volailles-terroir.example",
        phone="+33123456790",
        payment_terms_days=15,
        lead_time_days=1,
    )
    epicier = Supplier(
        name="Épices & Co",
        contact_name="M. Haddad",
        email="pro@epices-co.example",
        phone="+33123456791",
        payment_terms_days=45,
        lead_time_days=3,
    )
    session.add_all([abattoir, volailler, epicier])
    await session.flush()

    def _supplier_for(sku: str) -> Supplier:
        if sku.startswith(("POULET", "DINDE", "SAUCISSE")):
            return volailler
        if sku.startswith("EPICE"):
            return epicier
        return abattoir

    # --- Produits + stocks --------------------------------------------------
    products: dict[str, Product] = {}
    for sku, name, unit, price, perishable, dlc, _base in _PRODUCTS:
        p = Product(
            sku=f"{_SKU_PREFIX}{sku}",
            name=name,
            category="boucherie",
            family="epice" if sku.startswith("EPICE") else "viande",
            unit=unit,
            unit_price=price,
            perishable=perishable,
            shelf_life_days=dlc,
            supplier=_supplier_for(sku),
        )
        session.add(p)
        products[sku] = p
    await session.flush()

    # Stocks : la majorité confortables, quelques cas volontaires pour allumer les agents.
    # - stock bas (< seuil) → alerte STOCK_LOW + suggestion de réassort
    # - lot périssable en fin de vie + surplus → suggestion de démarque (anti-gaspi)
    low_stock = {"BOEUF-HACHE": 3.0, "POULET-ESCALOPE": 2.0}
    # Surplus volontairement supérieur à ce que la demande peut écouler avant la DLC
    # → l'agent Démarque propose une remise (sinon perte sèche).
    near_expiry = {
        "VEAU-ESCALOPE": (14.0, today + timedelta(days=1)),
        "FOIE-VOLAILLE": (8.0, today + timedelta(days=1)),
        "AGNEAU-GIGOT": (10.0, today + timedelta(days=1)),
    }
    for sku, p in products.items():
        base = next(row[6] for row in _PRODUCTS if row[0] == sku)
        threshold = round(base * 1.2, 1)
        if sku in near_expiry:
            qty, expiry = near_expiry[sku]
            session.add(
                Stock(product=p, quantity=qty, reorder_threshold=threshold, expiry_date=expiry)
            )
        elif sku in low_stock:
            session.add(Stock(product=p, quantity=low_stock[sku], reorder_threshold=threshold))
        else:
            session.add(
                Stock(product=p, quantity=round(base * 2.5, 1), reorder_threshold=threshold)
            )

    # --- Historique de ventes (90 jours, saisonnalité) ----------------------
    base_day = datetime.now(UTC) - timedelta(days=_HISTORY_DAYS)
    sales_count = 0
    for sku, p in products.items():
        if sku.startswith("EPICE"):
            continue  # ingrédient de production, non vendu au détail
        base = next(row[6] for row in _PRODUCTS if row[0] == sku)
        price = float(p.unit_price or 0.0)
        for d in range(_HISTORY_DAYS):
            day_dt = base_day + timedelta(days=d)
            qty = _demand(base, day_dt.date(), d)
            if qty <= 0:
                continue
            session.add(
                Sale(
                    product_id=p.id,
                    quantity=qty,
                    unit_price=price,
                    total=round(qty * price, 2),
                    sold_at=day_dt,
                )
            )
            sales_count += 1

    # --- Factures fournisseurs (échéancier + trésorerie) --------------------
    # Non payées, échéances étalées → buckets retard/7j/30j/+ de la page Payables.
    unpaid = [
        ("FAC-2026-101", abattoir, today - timedelta(days=40), today - timedelta(days=10), 1250.0),
        ("FAC-2026-102", volailler, today - timedelta(days=10), today + timedelta(days=5), 680.0),
        ("FAC-2026-103", abattoir, today - timedelta(days=5), today + timedelta(days=25), 1420.0),
        ("FAC-2026-104", epicier, today - timedelta(days=3), today + timedelta(days=42), 210.0),
        ("FAC-2026-105", volailler, today - timedelta(days=2), None, 350.0),
    ]
    for number, supplier, issued, due, amount in unpaid:
        inv = Invoice(
            number=number,
            supplier=supplier,
            issue_date=issued,
            due_date=due,
            currency="EUR",
            status=InvoiceStatus.APPROVED,
            ocr_status=OcrStatus.DONE,
            total_amount=amount,
            paid=False,
        )
        inv.lines.append(
            InvoiceLine(
                description="Livraison marchandise",
                quantity=1,
                unit_price=amount,
                line_total=amount,
            )
        )
        session.add(inv)

    # Payées (historique) → alimentent la marge / le pilotage.
    paid = [
        ("FAC-2026-090", abattoir, today - timedelta(days=35), 1100.0),
        ("FAC-2026-091", volailler, today - timedelta(days=28), 540.0),
    ]
    for number, supplier, issued, amount in paid:
        inv = Invoice(
            number=number,
            supplier=supplier,
            issue_date=issued,
            due_date=issued + timedelta(days=supplier.payment_terms_days),
            currency="EUR",
            status=InvoiceStatus.PAID,
            ocr_status=OcrStatus.DONE,
            total_amount=amount,
            paid=True,
            paid_at=datetime.now(UTC) - timedelta(days=5),
        )
        inv.lines.append(
            InvoiceLine(
                description="Livraison marchandise",
                quantity=1,
                unit_price=amount,
                line_total=amount,
            )
        )
        session.add(inv)

    # --- Clients + fidélité (RGPD : opt-in explicite) -----------------------
    fatima = Customer(
        name="Fatima", phone="+33600000001", consent_opt_in=True, consent_at=datetime.now(UTC)
    )
    karim = Customer(
        name="Karim", phone="+33600000002", consent_opt_in=True, consent_at=datetime.now(UTC)
    )
    sophie = Customer(
        name="Sophie", phone="+33600000003", consent_opt_in=True, consent_at=datetime.now(UTC)
    )
    marc = Customer(name="Marc", phone="+33600000004", consent_opt_in=False)
    session.add_all([fatima, karim, sophie, marc])
    await session.flush()

    for customer, balance in ((fatima, 120), (karim, 85), (sophie, 40)):
        account = LoyaltyAccount(
            customer_id=customer.id, points_balance=balance, lifetime_points=balance
        )
        session.add(account)
        await session.flush()
        session.add(
            LoyaltyTransaction(
                account_id=account.id,
                customer_id=customer.id,
                kind=LoyaltyTxnKind.EARN,
                points=balance,
                amount=float(balance),
                reason="Achats cumulés (démo)",
            )
        )

    # --- Réservations click & collect (cycle HITL complet) ------------------
    # Lignes passées au constructeur (relationship) : pas d'accès post-flush → pas
    # de lazy-load async (MissingGreenlet). Cf. CLAUDE.md §6.
    def _resa_line(product: Product, qty: float) -> ReservationLine:
        price = float(product.unit_price or 0)
        return ReservationLine(
            product_id=product.id,
            product_name=product.name,
            quantity=qty,
            unit_price=price,
            line_total=round(price * qty, 2),
        )

    bavette = products["BOEUF-BAVETTE"]
    poulet = products["POULET-ENTIER"]
    merguez = products["MERGUEZ"]
    # Une collectée (passée, fidélité déjà créditée) → alimente le tableau d'impact.
    collected = Reservation(
        customer_id=fatima.id,
        customer_name=fatima.name,
        customer_phone=fatima.phone,
        status=ReservationStatus.COLLECTED,
        pickup_date=today - timedelta(days=2),
        loyalty_credited=True,
        notes="Retirée samedi matin.",
        total_amount=round(float(bavette.unit_price or 0) * 2, 2),
        lines=[_resa_line(bavette, 2)],
    )
    # Une confirmée (à retirer demain) + une en attente de validation.
    confirmed = Reservation(
        customer_id=karim.id,
        customer_name=karim.name,
        customer_phone=karim.phone,
        status=ReservationStatus.CONFIRMED,
        pickup_date=today + timedelta(days=1),
        notes="Poulet pour dimanche.",
        total_amount=float(poulet.unit_price or 0),
        lines=[_resa_line(poulet, 1)],
    )
    pending = Reservation(
        customer_id=sophie.id,
        customer_name=sophie.name,
        customer_phone=sophie.phone,
        status=ReservationStatus.PENDING,
        pickup_date=today + timedelta(days=2),
        notes="3 kg de merguez pour un barbecue.",
        total_amount=round(float(merguez.unit_price or 0) * 3, 2),
        lines=[_resa_line(merguez, 3)],
    )
    session.add_all([collected, confirmed, pending])
    await session.flush()

    # --- Production : recette merguez maison (nomenclature) -----------------
    recipe = Recipe(
        product_id=merguez.id,
        name="Merguez maison (fournée)",
        yield_quantity=10,
        unit="kg",
        notes="Fournée de 10 kg — bœuf haché assaisonné.",
    )
    recipe.items.append(
        RecipeItem(ingredient_product_id=products["BOEUF-HACHE"].id, quantity=8, unit="kg")
    )
    recipe.items.append(
        RecipeItem(ingredient_product_id=products["EPICE-MERGUEZ"].id, quantity=0.5, unit="kg")
    )
    session.add(recipe)

    # --- Chaîne du froid : 2 frigos + 1 congélateur (un capteur en dérive) --
    session.add_all(
        [
            Equipment(
                name="Vitrine réfrigérée",
                kind=EquipmentKind.FRIDGE,
                location="Magasin",
                min_temp_c=0,
                max_temp_c=4,
                sensor_external_id="sensor-fridge-1",
            ),
            Equipment(
                name="Chambre froide réserve",
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
    await session.flush()

    log.info(
        "seed_demo.business",
        products=len(products),
        sales=sales_count,
        invoices=len(unpaid) + len(paid),
    )


async def _apply_top_markdowns(session: AsyncSession, org_id: int, limit: int = 2) -> int:
    """Applique les meilleures démarques suggérées → cash récupéré visible dans l'Impact."""
    rows = (
        (
            await session.execute(
                select(MarkdownSuggestion)
                .where(
                    MarkdownSuggestion.organization_id == org_id,
                    MarkdownSuggestion.status == MarkdownStatus.SUGGESTED,
                )
                .order_by(MarkdownSuggestion.score.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    for sug in rows:
        sug.status = MarkdownStatus.APPLIED
    await session.flush()
    return len(rows)


async def seed_demo() -> None:
    configure_logging()
    log.info("seed_demo.start", slug=DEMO_SLUG)

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(func.count()).select_from(Organization).where(Organization.slug == DEMO_SLUG)
        )
        if existing:
            log.info("seed_demo.skip", reason="org boucherie-demo already present")
            return

        # Référentiels globaux (idempotents) requis par le cycle quotidien.
        from app.ingestion.signals_ext import seed_signal_definitions
        from app.intelligence.finance.categories import seed_expense_categories
        from app.services.signals_service import ingest_signals

        await seed_expense_categories(session)
        await seed_signal_definitions(session)
        _today = date.today()
        await ingest_signals(session, date_from=_today - timedelta(days=200), date_to=_today)

        org = Organization(name="Boucherie Démo", slug=DEMO_SLUG, business_type="boucherie")
        session.add(org)
        role = await _get_or_create_owner_role(session)
        owner = User(
            email=DEMO_OWNER_EMAIL,
            full_name="Boucher Démo",
            hashed_password=hash_password(settings.seed_admin_password),
            role=role,
        )
        session.add(owner)
        await session.flush()
        session.add(Membership(user_id=owner.id, organization_id=org.id, role=MembershipRole.OWNER))

        # Abonnement (le commerce apparaît dans le backoffice plateforme avec un plan).
        from app.models import Plan, Subscription, SubscriptionStatus

        session.add(
            Subscription(
                organization_id=org.id,
                plan=Plan.PRO,
                status=SubscriptionStatus.ACTIVE,
                mrr_eur=49.0,
                started_on=_today.isoformat(),
            )
        )

        # Estampillage automatique sur l'org démo. Le commit reste DANS le contexte.
        with tenant_context(org.id):
            await _seed_boucherie(session, org, owner)

            # Chaîne du froid : relevés capteurs (mock keyless) → statut + registre HACCP.
            from app.services.iot.temperature_service import poll_readings

            await poll_readings(session, user_id=owner.id)

            # Cycle quotidien complet : snapshot, signaux, reco, alertes, briefing
            # (rafraîchit démarque + production au passage).
            from app.services.pipeline_service import run_job

            await run_job(session, "daily")

            # MLOps : bootstrap du registre de modèles (une version par produit).
            from app.models.model_artifact import RetrainTrigger
            from app.services.model_registry_service import retrain_all

            await retrain_all(session, trigger=RetrainTrigger.SEED)

            # Human-in-the-loop : on applique 2 démarques → cash récupéré dans l'Impact.
            applied = await _apply_top_markdowns(session, org.id)

            await session.commit()

        log.info("seed_demo.done", organization=org.slug, markdowns_applied=applied)
        log.info(
            "seed_demo.login",
            email=DEMO_OWNER_EMAIL,
            password_hint="settings.seed_admin_password",
        )


if __name__ == "__main__":
    asyncio.run(seed_demo())
