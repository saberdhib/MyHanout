"""Normalisation des données extraites (unités, libellés, rapprochement SKU)."""

from __future__ import annotations

import re

_UNIT_ALIASES = {
    "kgs": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "unite": "unit",
    "u": "unit",
    "litre": "L",
    "l": "L",
}


def normalize_unit(raw: str) -> str:
    """Normalise une unité de mesure vers une forme canonique."""
    key = raw.strip().lower()
    return _UNIT_ALIASES.get(key, key or "unit")


def normalize_label(raw: str) -> str:
    """Nettoie un libellé produit (espaces, casse)."""
    return re.sub(r"\s+", " ", raw).strip()


def slugify_sku(label: str) -> str:
    """Génère un SKU candidat à partir d'un libellé (rapprochement futur)."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", label.strip().upper())
    return cleaned.strip("-")[:64]
