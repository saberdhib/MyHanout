import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LogoWordmark } from "./Logo";
import { Icons } from "./icons";
import ChatWidget from "./ChatWidget";
import TourGuide from "./TourGuide";
import { t } from "../i18n";
import { useTheme } from "../hooks/useTheme";
import { getModules, platformRole } from "../api/client";

// `module` = clé du socle (cf. backend app/core/modules.py) ; null = toujours visible.
// `platformOnly` = visible uniquement pour un opérateur MyHanout (backoffice SaaS).
type Item = {
  to: string;
  label: string;
  icon: keyof typeof Icons;
  end?: boolean;
  module?: string;
  platformOnly?: boolean;
};

// Navigation regroupée par intention (lisibilité + repérage).
const groups: { title: string; items: Item[] }[] = [
  {
    title: "Pilotage",
    items: [
      { to: "/", label: "Dashboard", icon: "dashboard", end: true, module: "dashboard" },
      { to: "/briefing", label: "Briefing du matin", icon: "calendar", module: "briefing" },
      { to: "/report", label: "Bilan hebdo", icon: "finance", module: "report" },
      {
        to: "/recommendations",
        label: "Recommandations",
        icon: "suggest",
        module: "recommendations",
      },
      { to: "/alerts", label: "Alertes", icon: "quality", module: "alerts" },
      { to: "/chat", label: "Assistant", icon: "chat", module: "chat" },
      { to: "/finance", label: "Finance", icon: "finance", module: "finance" },
    ],
  },
  {
    title: "Commerce",
    items: [
      { to: "/promos", label: "Promos flash", icon: "promo", module: "promos" },
      { to: "/markdown", label: "Démarque", icon: "promo", module: "markdown" },
      { to: "/loyalty", label: "Fidélité", icon: "promo", module: "loyalty" },
      { to: "/reengagement", label: "Relance client", icon: "chat", module: "reengagement" },
      { to: "/production", label: "Production", icon: "forecast", module: "production" },
      { to: "/boucherie", label: "Boucherie", icon: "supplier", module: "meat" },
      { to: "/catalog", label: "Catalogue", icon: "stocks", module: "catalog" },
      { to: "/pricing", label: "Prix conseillés", icon: "finance", module: "pricing" },
      { to: "/stocks", label: "Stocks", icon: "stocks", module: "stocks" },
      { to: "/forecasts", label: "Prévisions", icon: "forecast", module: "forecasts" },
      { to: "/suggestions", label: "Suggestions", icon: "suggest", module: "suggestions" },
    ],
  },
  {
    title: "Quotidien",
    items: [
      { to: "/staffing", label: "Effectifs", icon: "calendar", module: "staffing" },
      { to: "/controls", label: "Contrôles & pertes", icon: "quality", module: "controls" },
      { to: "/end-of-day", label: "Fin de journée", icon: "calendar", module: "end_of_day" },
      { to: "/equipment", label: "Équipements", icon: "thermometer", module: "cold_chain" },
      { to: "/haccp", label: "Hygiène (HACCP)", icon: "quality", module: "haccp" },
      { to: "/quality", label: "Qualité (écarts)", icon: "quality", module: "quality" },
      { to: "/invoices", label: "Factures", icon: "invoice", module: "invoices" },
    ],
  },
  {
    title: "Données",
    items: [
      { to: "/data-ops", label: "Data Ops", icon: "plug", module: "dataops" },
      { to: "/connectors", label: "Connecteurs", icon: "plug", module: "integrations" },
      { to: "/integrations", label: "Intégrations", icon: "plug", module: "integrations" },
      { to: "/suppliers", label: "Fournisseurs", icon: "supplier", module: "suppliers" },
      { to: "/support", label: "Aide & support", icon: "chat", module: "support" },
      { to: "/settings", label: "Réglages", icon: "plug" },
    ],
  },
  {
    title: "MyHanout Ops",
    items: [{ to: "/admin", label: "Backoffice", icon: "dashboard", platformOnly: true }],
  },
];

const allItems = groups.flatMap((g) => g.items);

export default function Layout() {
  const { theme, toggle } = useTheme();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false); // sidebar mobile (off-canvas)
  // Modules actifs selon le type de commerce (socle générique configurable).
  const [enabled, setEnabled] = useState<string[] | null>(null);
  // Opérateur plateforme MyHanout ? (débloque le groupe backoffice).
  const isPlatform = Boolean(platformRole());
  const current =
    allItems.find((i) => (i.end ? pathname === i.to : pathname.startsWith(i.to) && i.to !== "/")) ??
    allItems[0];

  useEffect(() => {
    getModules()
      .then((m) => setEnabled(m.enabled))
      .catch(() => setEnabled(null)); // dégradé : on montre tout si l'appel échoue
  }, []);

  // Filtre par module actif (null = pas encore chargé / échec → tout visible)
  // + masque le backoffice aux non-opérateurs.
  const visible = (i: Item) =>
    (!i.platformOnly || isPlatform) &&
    (!i.module || enabled === null || enabled.includes(i.module));

  // Referme la sidebar à chaque navigation (mobile).
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div className="flex min-h-screen bg-surface dark:bg-night">
      {/* Voile mobile derrière la sidebar ouverte */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-night/50 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ---- Sidebar (off-canvas sur mobile, fixe sur desktop) ---- */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen w-64 transform flex-col bg-night text-white transition-transform duration-200 lg:sticky lg:top-0 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center px-5">
          <LogoWordmark />
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
          {groups
            .map((g) => ({ ...g, items: g.items.filter(visible) }))
            .filter((g) => g.items.length > 0)
            .map((g) => (
            <div key={g.title}>
              <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/35">
                {t(g.title)}
              </div>
              <div className="space-y-0.5">
                {g.items.map((l) => {
                  const Icon = Icons[l.icon];
                  return (
                    <NavLink
                      key={l.to}
                      to={l.to}
                      end={l.end}
                      className={({ isActive }) =>
                        `group relative flex items-center gap-3 rounded-card px-3 py-2 text-sm transition-colors ${
                          isActive
                            ? "bg-white/10 font-semibold text-white"
                            : "text-white/65 hover:bg-white/5 hover:text-white"
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-brand" />
                          )}
                          <Icon className={isActive ? "text-brand-light" : "text-white/55 group-hover:text-white"} />
                          <span>{t(l.label)}</span>
                        </>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bloc commerce / utilisateur */}
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-3 rounded-card px-2 py-2">
            <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-brand font-bold text-white">
              CD
            </span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">Commerce Démo</div>
              <div className="truncate text-xs text-white/45">Propriétaire</div>
            </div>
          </div>
        </div>
      </aside>

      {/* ---- Zone principale ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-night/[0.06] bg-surface/80 px-4 backdrop-blur-xl sm:px-8 dark:border-white/10 dark:bg-night/80">
          <div className="flex items-center gap-3 text-sm text-night/50 dark:text-surface/50">
            <button
              onClick={() => setOpen(true)}
              aria-label="Ouvrir le menu"
              className="flex h-9 w-9 items-center justify-center rounded-card border border-night/10 lg:hidden dark:border-white/15"
            >
              ☰
            </button>
            <span className="hidden sm:inline">MyHanout</span>
            <span className="hidden text-night/25 sm:inline dark:text-surface/25">/</span>
            <span className="font-semibold text-night dark:text-surface">{t(current.label)}</span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://wa.me/0000000000"
              className="hidden items-center gap-2 rounded-pill bg-brand/10 px-3 py-1.5 text-xs font-semibold text-brand-dark dark:text-brand-light sm:flex"
            >
              💬 Assistant WhatsApp
            </a>
            <button
              onClick={toggle}
              aria-label="Basculer le thème"
              className="flex h-9 w-9 items-center justify-center rounded-card border border-night/10 text-base hover:bg-night/5 dark:border-white/15 dark:hover:bg-white/10"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-8 sm:py-8 dark:text-surface">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Fenêtre de chat flottante, disponible partout. */}
      <ChatWidget />
      <TourGuide />
    </div>
  );
}
