"""Règles de fidélité — pures, déterministes, explicables (aucune I/O).

- `points_for_amount` : points gagnés pour un montant d'achat.
- `reward_status` : où en est le client vis-à-vis de la prochaine récompense.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def points_for_amount(amount: float, points_per_euro: float) -> int:
    """Points entiers gagnés (arrondi bas). Négatif/zéro → 0."""
    if amount <= 0 or points_per_euro <= 0:
        return 0
    return int(math.floor(amount * points_per_euro))


@dataclass
class RewardStatus:
    balance: int
    threshold: int
    reward_ready: bool
    points_to_next: int
    rewards_available: int  # nombre de récompenses échangeables avec le solde
    explanation: str


def reward_status(balance: int, threshold: int, reward_label: str) -> RewardStatus:
    if threshold <= 0:
        return RewardStatus(balance, threshold, False, 0, 0, "Aucun palier de récompense défini.")
    ready = balance >= threshold
    to_next = 0 if ready else threshold - balance
    available = balance // threshold
    if ready:
        expl = (
            f"{available} × « {reward_label} » disponible(s) ({balance} pts, palier {threshold})."
        )
    else:
        expl = f"Encore {to_next} pts pour « {reward_label} » (palier {threshold})."
    return RewardStatus(balance, threshold, ready, to_next, available, expl)
