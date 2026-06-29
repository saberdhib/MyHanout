"""Référentiel canonique des catégories de charges (source unique).

Utilisé par : la migration (insertion globale), le seed, le classifieur mock et
le helper d'upsert pour les tests. `kind` = OPEX (exploitation) ou CAPEX
(investissement immobilisable).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ExpenseKind
from app.models.expense import ExpenseCategory

# (code, label, kind, accounting_hint)
CATEGORIES: list[tuple[str, str, ExpenseKind, str | None]] = [
    ("MERCHANDISE", "Marchandises / Stock", ExpenseKind.OPEX, "607"),
    ("TELECOM", "Téléphonie / Internet", ExpenseKind.OPEX, "626"),
    ("ENERGY", "Énergie (élec/gaz/eau)", ExpenseKind.OPEX, "606"),
    ("RENT", "Loyer / Charges locatives", ExpenseKind.OPEX, "613"),
    ("SUPPLIES", "Consommables / Fournitures", ExpenseKind.OPEX, "606"),
    ("INSURANCE", "Assurance", ExpenseKind.OPEX, "616"),
    ("MAINTENANCE", "Entretien / Réparations", ExpenseKind.OPEX, "615"),
    ("SERVICES", "Services / Honoraires", ExpenseKind.OPEX, "622"),
    ("TAXES", "Taxes / Cotisations", ExpenseKind.OPEX, "63"),
    ("EQUIPMENT", "Matériel / Équipement", ExpenseKind.CAPEX, "215"),
    ("OTHER", "Autre", ExpenseKind.OPEX, None),
]

CATEGORY_KIND: dict[str, ExpenseKind] = {c[0]: c[2] for c in CATEGORIES}


async def seed_expense_categories(session: AsyncSession) -> int:
    """Upsert idempotent du référentiel global (par `code`). Renvoie le nb créé."""
    created = 0
    for code, label, kind, hint in CATEGORIES:
        existing = await session.scalar(select(ExpenseCategory).where(ExpenseCategory.code == code))
        if existing is None:
            session.add(ExpenseCategory(code=code, label=label, kind=kind, accounting_hint=hint))
            created += 1
    await session.flush()
    return created
