import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/stocks", label: "Stocks" },
  { to: "/forecasts", label: "Prévisions" },
  { to: "/suggestions", label: "Suggestions" },
  { to: "/end-of-day", label: "Fin de journée" },
  { to: "/quality", label: "Qualité (écarts)" },
  { to: "/invoices", label: "Factures" },
  { to: "/suppliers", label: "Fournisseurs" },
];

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 bg-brand-dark text-white flex flex-col">
        <div className="px-5 py-5 text-xl font-bold border-b border-white/10">
          🏪 MyHanout AI
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm ${
                  isActive ? "bg-white/20 font-semibold" : "hover:bg-white/10"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 text-xs text-white/60">v0.1.0 — MVP</div>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
