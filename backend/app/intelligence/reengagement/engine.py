"""Segmentation de relance client — pure, déterministe, explicable (aucune I/O).

À partir du solde de fidélité et de la dernière activité, classe un client dans AU PLUS
un segment (priorité : récompense prête > presque récompense > inactif) et propose un
message de relance. Le commerçant valide et déclenche l'envoi (human-in-the-loop, RGPD).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class Segment(enum.StrEnum):
    REWARD_READY = "reward_ready"  # a atteint le palier → l'inciter à venir récupérer
    ALMOST_REWARD = "almost_reward"  # tout proche du palier → l'inciter à revenir acheter
    INACTIVE = "inactive"  # pas d'activité depuis longtemps → reconquête


@dataclass
class SegmentDecision:
    segment: Segment | None
    message: str
    explanation: str


def classify(
    *,
    balance: int,
    threshold: int,
    days_since_last: int | None,
    reward_label: str,
    almost_gap: int,
    inactive_days: int,
) -> SegmentDecision:
    """Classe un client + rédige le message. `segment=None` si aucun ciblage pertinent."""
    if threshold > 0 and balance >= threshold:
        return SegmentDecision(
            Segment.REWARD_READY,
            f"Bonne nouvelle 🎁 vous avez {balance} points : passez chercher votre "
            f"« {reward_label} » !",
            f"Solde {balance} ≥ palier {threshold} : récompense disponible.",
        )
    if threshold > 0 and (threshold - almost_gap) <= balance < threshold:
        need = threshold - balance
        return SegmentDecision(
            Segment.ALMOST_REWARD,
            f"Plus que {need} points pour votre « {reward_label} » ✨ à très vite !",
            f"Solde {balance} à {need} pts du palier {threshold} (fenêtre {almost_gap}).",
        )
    if days_since_last is not None and days_since_last >= inactive_days:
        return SegmentDecision(
            Segment.INACTIVE,
            "Ça fait un moment qu'on ne vous a pas vu 🙂 vos points vous attendent !",
            f"Aucune activité depuis {days_since_last} j (seuil {inactive_days} j).",
        )
    return SegmentDecision(None, "", "Client engagé : pas de relance nécessaire.")
