"""Socle retail générique : modules activables par type de commerce (vertical).

Le produit est **générique d'abord, paramétrable ensuite**. Chaque fonctionnalité
métier est un *module* identifié par une clé. Un **profil** (type de commerce) active
un sous-ensemble de modules. Par défaut, tout est activé (générique) ; un profil ne
fait que **désactiver** ce qui n'a pas de sens pour ce vertical.

Ajouter un vertical = ajouter une entrée dans `PROFILE_DISABLES` (aucune logique
métier en dur dans le socle). Le frontend lit `/config/modules` et adapte la nav.
"""

from __future__ import annotations

# Catalogue des modules du socle (clé -> libellé).
MODULES: dict[str, str] = {
    "dashboard": "Tableau de bord",
    "briefing": "Briefing du matin",
    "report": "Bilan hebdo",
    "controls": "Contrôles & pertes",
    "recommendations": "Recommandations",
    "alerts": "Alertes",
    "dataops": "Data Ops",
    "chat": "Assistant IA",
    "pos": "Caisse / Ventes",
    "catalog": "Catalogue & prix",
    "stocks": "Stock & inventaire",
    "forecasts": "Prévisions",
    "suggestions": "Réassort",
    "promos": "Promotions",
    "loyalty": "Fidélité client",
    "reengagement": "Relance client",
    "reservations": "Réservations (click & collect)",
    "markdown": "Démarque (anti-gaspi)",
    "production": "Production & recettes",
    "pricing": "Prix conseillés",
    "staffing": "Effectifs",
    "finance": "Finance",
    "invoices": "Factures",
    "suppliers": "Fournisseurs",
    "customers": "Clients / CRM",
    "end_of_day": "Fin de journée",
    "quality": "Qualité (écarts)",
    "cold_chain": "Chaîne du froid",
    "haccp": "Hygiène (HACCP)",
    "integrations": "Intégrations",
    "meat": "Boucherie (traçabilité)",
    "support": "Aide & support",
}

# Modules toujours présents (socle minimal).
CORE = {"dashboard", "chat", "catalog", "stocks", "finance", "suppliers", "support"}

# Par profil (type de commerce) : modules DÉSACTIVÉS. Le reste est actif.
# Profil inconnu -> rien de désactivé (générique complet).
PROFILE_DISABLES: dict[str, set[str]] = {
    "boucherie": set(),  # tout, y compris boucherie + chaîne du froid
    "epicerie": set(),  # alimentation générale (démo) : tout
    "alimentation_generale": set(),
    "superette": {"meat"},
    "primeur": {"meat"},
    "boulangerie": {"meat"},
    "magasin_specialise": {"meat", "cold_chain"},
}


def enabled_modules_for(business_type: str | None) -> list[str]:
    """Liste des modules actifs pour un type de commerce (générique par défaut)."""
    disabled = PROFILE_DISABLES.get((business_type or "").lower(), set())
    disabled -= CORE  # on ne désactive jamais le socle
    return [key for key in MODULES if key not in disabled]
