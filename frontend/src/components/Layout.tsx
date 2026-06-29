import { NavLink, Outlet } from "react-router-dom";
import { LogoWordmark } from "./Logo";
import { useTheme } from "../hooks/useTheme";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/chat", label: "Assistant" },
  { to: "/promos", label: "Promos flash" },
  { to: "/finance", label: "Finance" },
  { to: "/stocks", label: "Stocks" },
  { to: "/forecasts", label: "Prévisions" },
  { to: "/suggestions", label: "Suggestions" },
  { to: "/end-of-day", label: "Fin de journée" },
  { to: "/quality", label: "Qualité (écarts)" },
  { to: "/invoices", label: "Factures" },
  { to: "/integrations", label: "Intégrations" },
  { to: "/suppliers", label: "Fournisseurs" },
];

export default function Layout() {
  const { theme, toggle } = useTheme();
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 bg-night text-white flex flex-col">
        <div className="flex items-center justify-between px-5 py-5 border-b border-white/10">
          <LogoWordmark />
          <button
            onClick={toggle}
            aria-label="Basculer le thème"
            className="rounded-card p-1.5 text-lg hover:bg-white/10"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `block rounded-card px-3 py-2 text-sm ${
                  isActive ? "bg-brand/20 font-semibold text-brand-light" : "hover:bg-white/10"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 text-xs text-white/60">v0.1.0 — MVP</div>
      </aside>
      <main className="flex-1 bg-surface/60 p-8 dark:bg-night dark:text-surface">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
