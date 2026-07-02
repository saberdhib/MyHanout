/**
 * i18n léger : français par défaut, anglais en option (Réglages).
 *
 * Principe volontairement simple : `t("libellé français")` renvoie la traduction
 * anglaise si la langue est "en", sinon le libellé tel quel. Le dictionnaire couvre
 * la coquille de l'app (navigation, header, réglages, tour) et s'étend au besoin —
 * il suffit d'ajouter des paires FR → EN ci-dessous.
 *
 * Le changement de langue recharge la page (robuste, pas de plomberie de contexte).
 */

export type Lang = "fr" | "en";

const EN: Record<string, string> = {
  // Groupes de navigation
  Pilotage: "Steering",
  Commerce: "Store",
  Quotidien: "Daily",
  Données: "Data",
  // Entrées de navigation
  Dashboard: "Dashboard",
  "Briefing du matin": "Morning briefing",
  "Bilan hebdo": "Weekly report",
  Recommandations: "Recommendations",
  Alertes: "Alerts",
  Assistant: "Assistant",
  Finance: "Finance",
  "Promos flash": "Flash promos",
  Démarque: "Markdowns",
  Production: "Production",
  Boucherie: "Butchery",
  Catalogue: "Catalog",
  "Prix conseillés": "Suggested prices",
  Stocks: "Inventory",
  Prévisions: "Forecasts",
  Suggestions: "Suggestions",
  Effectifs: "Staffing",
  "Contrôles & pertes": "Controls & losses",
  "Fin de journée": "End of day",
  Équipements: "Equipment",
  "Hygiène (HACCP)": "Hygiene (HACCP)",
  "Qualité (écarts)": "Quality (gaps)",
  Factures: "Invoices",
  "Data Ops": "Data Ops",
  Connecteurs: "Connectors",
  Intégrations: "Integrations",
  Fournisseurs: "Suppliers",
  Réglages: "Settings",
  "MyHanout Ops": "MyHanout Ops",
  Backoffice: "Backoffice",
  "Aide & support": "Help & support",
  Fidélité: "Loyalty",
  "Relance client": "Re-engagement",
  Réservations: "Reservations",
  Échéancier: "Payables",
  "Impact (€)": "Impact (€)",
  // Header / commun
  "Assistant WhatsApp": "WhatsApp assistant",
  "Basculer le thème": "Toggle theme",
  "Ouvrir le menu": "Open menu",
  // Réglages
  Préférences: "Preferences",
  Thème: "Theme",
  Clair: "Light",
  Sombre: "Dark",
  Langue: "Language",
  Français: "French",
  Anglais: "English",
  "Revoir le tour de bienvenue": "Replay the welcome tour",
  "Vos préférences sont enregistrées sur cet appareil.":
    "Your preferences are saved on this device.",
  // Tour de bienvenue
  "Bienvenue sur MyHanout AI 👋": "Welcome to MyHanout AI 👋",
  Passer: "Skip",
  Suivant: "Next",
  "C'est parti !": "Let's go!",
};

export function getLang(): Lang {
  const saved = localStorage.getItem("lang");
  return saved === "en" ? "en" : "fr";
}

export function setLang(lang: Lang): void {
  localStorage.setItem("lang", lang);
  window.location.reload(); // simple et robuste : tout se re-rend dans la bonne langue
}

/** Traduit un libellé français (identité en FR, dictionnaire en EN). */
export function t(fr: string): string {
  return getLang() === "en" ? (EN[fr] ?? fr) : fr;
}
