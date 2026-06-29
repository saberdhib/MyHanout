"""Évaluation des agents : précision du routage d'intention (offline, déterministe).

Jeu de cas (message → agent attendu). Mesure l'accuracy du routage de
l'orchestrateur. Base d'une suite d'éval extensible (golden set, LLM-as-judge).
"""

from __future__ import annotations

from pydantic import BaseModel

from app.intelligence.llm.orchestrator import get_orchestrator

# Cas d'évaluation : (message, agent attendu).
ROUTING_CASES: list[tuple[str, str]] = [
    ("je veux passer une commande de boeuf", "agent_order"),
    ("commande pour demain", "agent_order"),
    ("réassort épicerie", "agent_order"),
    ("rupture de stock sur le lait", "agent_stock"),
    ("quels produits en péremption ?", "agent_stock"),
    ("mes échéances de factures", "agent_finance"),
    ("point trésorerie du mois", "agent_finance"),
    ("propose une promo pour samedi", "agent_marketing"),
    ("génère une annonce", "agent_marketing"),
    ("bonjour, une question", "agent_support"),
]


class CaseResult(BaseModel):
    message: str
    expected: str
    actual: str
    ok: bool


class RoutingReport(BaseModel):
    total: int
    correct: int
    accuracy: float
    cases: list[CaseResult]


def evaluate_routing() -> RoutingReport:
    """Évalue la précision de routage de l'orchestrateur sur le golden set."""
    orch = get_orchestrator()
    from app.intelligence.llm.orchestrator import detect_intent

    results: list[CaseResult] = []
    for message, expected in ROUTING_CASES:
        agent = orch.select_agent(detect_intent(message))
        results.append(
            CaseResult(
                message=message, expected=expected, actual=agent.name, ok=agent.name == expected
            )
        )
    correct = sum(1 for r in results if r.ok)
    total = len(results)
    return RoutingReport(
        total=total,
        correct=correct,
        accuracy=round(correct / total, 3) if total else 0.0,
        cases=results,
    )
