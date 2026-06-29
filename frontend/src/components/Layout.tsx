import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LogoWordmark } from "./Logo";
import { Icons } from "./icons";
import { useTheme } from "../hooks/useTheme";

type Item = { to: string; label: string; icon: keyof typeof Icons; end?: boolean };

// Navigation regroupée par intention (lisibilité + repérage).
const groups: { title: string; items: Item[] }[] = [
  {
    title: "Pilotage",
    items: [
      { to: "/", label: "Dashboard", icon: "dashboard", end: true },
      { to: "/chat", label: "Assistant", icon: "chat" },
      { to: "/finance", label: "Finance", icon: "finance" },
    ],
  },
  {
    title: "Commerce",
    items: [
      { to: "/promos", label: "Promos flash", icon: "promo" },
      { to: "/stocks", label: "Stocks", icon: "stocks" },
      { to: "/forecasts", label: "Prévisions", icon: "forecast" },
      { to: "/suggestions", label: "Suggestions", icon: "suggest" },
    ],
  },
  {
    title: "Quotidien",
    items: [
      { to: "/end-of-day", label: "Fin de journée", icon: "calendar" },
      { to: "/quality", label: "Qualité (écarts)", icon: "quality" },
      { to: "/invoices", label: "Factures", icon: "invoice" },
    ],
  },
  {
    title: "Données",
    items: [
      { to: "/integrations", label: "Intégrations", icon: "plug" },
      { to: "/suppliers", label: "Fournisseurs", icon: "supplier" },
    ],
  },
];

const allItems = groups.flatMap((g) => g.items);

export default function Layout() {
  const { theme, toggle } = useTheme();
  const { pathname } = useLocation();
  const current =
    allItems.find((i) => (i.end ? pathname === i.to : pathname.startsWith(i.to) && i.to !== "/")) ??
    allItems[0];

  return (
    <div className="flex min-h-screen bg-surface dark:bg-night">
      {/* ---- Sidebar ---- */}
      <aside className="sticky top-0 flex h-screen w-64 flex-col bg-night text-white">
        <div className="flex h-16 items-center px-5">
          <LogoWordmark />
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
          {groups.map((g) => (
            <div key={g.title}>
              <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/35">
                {g.title}
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
                          <span>{l.label}</span>
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
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-night/[0.06] bg-surface/80 px-8 backdrop-blur-xl dark:border-white/10 dark:bg-night/80">
          <div className="flex items-center gap-2 text-sm text-night/50 dark:text-surface/50">
            <span>MyHanout</span>
            <span className="text-night/25 dark:text-surface/25">/</span>
            <span className="font-semibold text-night dark:text-surface">{current.label}</span>
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

        <main className="flex-1 px-8 py-8 dark:text-surface">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
