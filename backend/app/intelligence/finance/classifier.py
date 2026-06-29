"""Classifieur de charges (OPEX/CAPEX) — abstraction + mock keyless par défaut.

- `mock` : règles déterministes par mots-clés (fournisseur/libellé) → catégorie +
  kind + explication. Aucun réseau, reproductible.
- `llm` : réutilise le `LLMProvider` existant (claude|mistral|huggingface|mock) pour
  proposer une catégorie + kind + explication en langage naturel. Retombe sur le
  mock si la sortie du LLM est inexploitable.

Sans configuration → `mock` (keyless). Le résultat porte TOUJOURS une `explanation`.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.finance.categories import CATEGORY_KIND
from app.models.base import ExpenseKind

log = get_logger(__name__)


class ClassificationResult(BaseModel):
    category_code: str
    kind: ExpenseKind
    confidence: float
    explanation: str


class ExpenseClassifier(ABC):
    name: str = "abstract"

    @abstractmethod
    async def classify(
        self, *, supplier_name: str | None, label: str | None, total: float | None
    ) -> ClassificationResult:
        raise NotImplementedError


# Règles mot-clé → (code catégorie). Ordre = priorité (première correspondance).
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("orange", "sfr", "free", "bouygues", "telecom", "télécom", "internet", "mobile"), "TELECOM"),
    (
        (
            "edf",
            "engie",
            "energie",
            "énergie",
            "gaz",
            "electric",
            "électric",
            "eau",
            "veolia",
            "suez",
        ),
        "ENERGY",
    ),
    (("loyer", "bail", "sci ", "immobili"), "RENT"),
    (("assur", "axa", "maif", "allianz", "mutuelle", "groupama"), "INSURANCE"),
    (("entretien", "reparation", "réparation", "plomb", "maintenance", "nettoyage"), "MAINTENANCE"),
    (("comptable", "avocat", "honoraire", "conseil", "notaire", "agence"), "SERVICES"),
    (
        ("impot", "impôt", "taxe", "urssaf", "cotisation", "tresor public", "trésor public"),
        "TAXES",
    ),
    (
        (
            "carton",
            "sac",
            "emballage",
            "consommable",
            "fourniture",
            "papeterie",
            "etiquette",
            "étiquette",
        ),
        "SUPPLIES",
    ),
    (
        (
            "materiel",
            "matériel",
            "equipement",
            "équipement",
            "four",
            "frigo",
            "vitrine",
            "caisse",
            "ordinateur",
            "vehicule",
            "véhicule",
            "camion",
            "trancheuse",
        ),
        "EQUIPMENT",
    ),
]


class MockExpenseClassifier(ExpenseClassifier):
    name = "mock"

    async def classify(
        self, *, supplier_name: str | None, label: str | None, total: float | None
    ) -> ClassificationResult:
        haystack = f"{supplier_name or ''} {label or ''}".lower()
        for keywords, code in _RULES:
            hit = next((k for k in keywords if k.strip() in haystack), None)
            if hit:
                kind = CATEGORY_KIND[code]
                return ClassificationResult(
                    category_code=code,
                    kind=kind,
                    confidence=0.8,
                    explanation=(
                        f"Mot-clé « {hit.strip()} » détecté "
                        f"chez « {supplier_name or 'fournisseur'} » → {code} ({kind.value})."
                    ),
                )
        # Défaut : marchandise (cas le plus fréquent pour un commerce), confiance faible.
        return ClassificationResult(
            category_code="MERCHANDISE",
            kind=ExpenseKind.OPEX,
            confidence=0.4,
            explanation=(
                "Aucun mot-clé spécifique : classé en marchandises par défaut (à confirmer)."
            ),
        )


class LLMExpenseClassifier(ExpenseClassifier):
    """Classifieur via le LLMProvider existant ; fallback mock si sortie inexploitable."""

    name = "llm"

    def __init__(self) -> None:
        self._mock = MockExpenseClassifier()

    async def classify(
        self, *, supplier_name: str | None, label: str | None, total: float | None
    ) -> ClassificationResult:
        from app.intelligence.llm import LLMMessage, get_llm_provider

        codes = ", ".join(CATEGORY_KIND.keys())
        system = (
            "Tu catégorises une facture de commerçant. Réponds en JSON strict "
            '{"category_code","kind","confidence","explanation"}. '
            f"category_code ∈ [{codes}] ; kind ∈ [opex, capex] ; confidence ∈ [0,1] ; "
            "explanation en français, courte."
        )
        user = (
            f"Fournisseur: {supplier_name or '?'} | Libellé: {label or '?'} | Total: {total or '?'}"
        )
        try:
            resp = await get_llm_provider().complete(
                [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]
            )
            data = json.loads(resp.content)
            code = str(data["category_code"]).upper()
            if code not in CATEGORY_KIND:
                raise ValueError(f"code inconnu: {code}")
            kind = ExpenseKind(str(data.get("kind", CATEGORY_KIND[code].value)).lower())
            explanation = str(data.get("explanation") or "").strip()
            if not explanation:
                raise ValueError("explanation vide")
            return ClassificationResult(
                category_code=code,
                kind=kind,
                confidence=float(data.get("confidence", 0.6)),
                explanation=explanation,
            )
        except Exception as exc:  # noqa: BLE001 - tout échec → fallback mock (keyless)
            log.warning("finance.classifier.llm_fallback", error=str(exc))
            return await self._mock.classify(supplier_name=supplier_name, label=label, total=total)


def get_expense_classifier() -> ExpenseClassifier:
    """Retourne le classifieur configuré. Sans config → mock (keyless)."""
    if settings.finance_classifier.lower() == "llm":
        return LLMExpenseClassifier()
    return MockExpenseClassifier()
