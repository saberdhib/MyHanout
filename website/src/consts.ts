// Constantes du site vitrine (source unique).
export const SITE = {
  name: "MyHanout AI",
  title: "MyHanout AI — Le copilote IA des commerces de proximité",
  description:
    "OCR de factures, prévision de la demande, réassort explicable et promos anti-gaspillage. " +
    "Piloté depuis WhatsApp/Telegram. Multi-tenant, RGPD, human-in-the-loop.",
  // URL de l'app (dashboard). Surchargée par PUBLIC_APP_URL au build si besoin.
  appUrl: import.meta.env.PUBLIC_APP_URL || "http://localhost:5173",
};

export const NAV = [
  { label: "Fonctions", href: "/#fonctions" },
  { label: "Tarifs", href: "/pricing" },
  { label: "Confiance & RGPD", href: "/confiance" },
  { label: "Contact", href: "/contact" },
];
