import { useEffect, useState } from "react";
import { Card, Stat } from "../components/Card";
import {
  classifyAll,
  confirmClassification,
  getExpenseCategories,
  getExpenses,
  getFinanceAlerts,
  getInventoryValue,
  getMargins,
  getTreasury,
  type ExpenseCategory,
  type ExpenseInvoice,
  type FinanceAlert,
  type InventoryValuation,
  type MarginReport,
  type TreasuryView,
} from "../api/client";

const eur = (n: number) =>
  n.toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

// Petite info-bulle d'explicabilité (le « pourquoi » d'un chiffre).
function Why({ text }: { text: string }) {
  return (
    <span
      title={text}
      className="ml-1 cursor-help text-night/30 dark:text-surface/30"
      aria-label={text}
    >
      ⓘ
    </span>
  );
}

const KIND_STYLE: Record<string, string> = {
  opex: "bg-brand/10 text-brand-dark dark:text-brand-light",
  capex: "bg-accent/15 text-accent",
  unknown: "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60",
};

export default function Finance() {
  const [treasury, setTreasury] = useState<TreasuryView | null>(null);
  const [inventory, setInventory] = useState<InventoryValuation | null>(null);
  const [margins, setMargins] = useState<MarginReport | null>(null);
  const [expenses, setExpenses] = useState<ExpenseInvoice[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [alerts, setAlerts] = useState<FinanceAlert[]>([]);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [t, inv, m, ex, cats, al] = await Promise.all([
      getTreasury(),
      getInventoryValue(),
      getMargins(),
      getExpenses(),
      getExpenseCategories(),
      getFinanceAlerts(),
    ]);
    setTreasury(t);
    setInventory(inv);
    setMargins(m);
    setExpenses(ex);
    setCategories(cats);
    setAlerts(al.alerts);
  }
  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  async function runClassifyAll() {
    setBusy(true);
    try {
      await classifyAll();
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function correct(inv: ExpenseInvoice, categoryId: number) {
    const cat = categories.find((c) => c.id === categoryId);
    if (!cat) return;
    await confirmClassification(inv.id, cat.id, cat.kind);
    await refresh();
  }

  const catLabel = (id: number | null) =>
    categories.find((c) => c.id === id)?.label ?? "—";

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">Finance</h1>
          <p className="page-sub">
            Pilotage (pré-compta) — estimations explicables, pas de comptabilité certifiée.
          </p>
        </div>
        <button onClick={runClassifyAll} disabled={busy} className="btn-primary disabled:opacity-50">
          {busy ? "Classification…" : "🪄 Classer les charges (IA)"}
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Solde estimé"
          value={treasury ? eur(treasury.estimated_balance) : "—"}
          icon="💶"
          hint="Ventes − factures payées"
        />
        <Stat
          label="À payer (30 j)"
          value={treasury ? eur(treasury.upcoming_30d) : "—"}
          icon="⏳"
          hint="Échéances à venir"
        />
        <Stat
          label="Valeur du stock"
          value={inventory ? eur(inventory.total_value) : "—"}
          icon="📦"
          hint={inventory ? `dont ${eur(inventory.at_risk_value)} à risque` : undefined}
        />
        <Stat
          label="Alertes finance"
          value={alerts.length}
          icon="🚨"
          hint="doublons, prix, marges, échéances"
        />
      </div>

      {/* Trésorerie + alertes */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          title="Trésorerie"
          subtitle={treasury ? `${treasury.period_from} → ${treasury.period_to}` : undefined}
        >
          {treasury && (
            <>
              <div className="space-y-2">
                {treasury.lines.map((l) => (
                  <div key={l.label} className="flex items-center justify-between text-sm">
                    <span className="text-night/70 dark:text-surface/70">
                      {l.label}
                      <Why text={l.explanation} />
                    </span>
                    <span
                      className={`font-semibold ${l.amount < 0 ? "text-red-500" : "text-brand-dark dark:text-brand-light"}`}
                    >
                      {eur(l.amount)}
                    </span>
                  </div>
                ))}
              </div>
              {treasury.alert && (
                <div className="mt-4 rounded-card bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10">
                  ⚠️ {treasury.alert}
                </div>
              )}
              <p className="mt-4 text-[11px] text-night/40 dark:text-surface/40">
                {treasury.disclaimer}
              </p>
            </>
          )}
        </Card>

        <Card title="Alertes finance" subtitle="Proposées — aucune action automatique">
          {alerts.length === 0 && (
            <p className="text-sm text-night/50 dark:text-surface/50">Aucune alerte. 🎉</p>
          )}
          <ul className="space-y-3">
            {alerts.map((a, i) => (
              <li key={i} className="rounded-card border border-night/[0.06] p-3 dark:border-white/10">
                <div className="flex items-center gap-2">
                  <span
                    className={`pill ${
                      a.severity === "critical"
                        ? "bg-red-100 text-red-700"
                        : a.severity === "warning"
                          ? "bg-accent/15 text-accent"
                          : "bg-brand/10 text-brand-dark dark:text-brand-light"
                    }`}
                  >
                    {a.severity}
                  </span>
                  <span className="text-sm font-semibold">{a.title}</span>
                </div>
                <p className="mt-1 text-xs text-night/60 dark:text-surface/60">{a.reason}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Marges */}
      <Card title="Marges par produit" subtitle={margins?.explanation}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-night/[0.06] text-left text-night/50 dark:border-white/10 dark:text-surface/50">
                <th className="py-2">Produit</th>
                <th className="text-right">Vendu</th>
                <th className="text-right">PV moyen</th>
                <th className="text-right">Coût</th>
                <th className="text-right">Marge/u</th>
                <th className="text-right">%</th>
                <th>Signal</th>
              </tr>
            </thead>
            <tbody>
              {(margins?.items ?? []).map((m) => (
                <tr key={m.product_id} className="border-b border-night/[0.04] last:border-0 dark:border-white/[0.06]">
                  <td className="py-2 font-medium">
                    {m.product_name ?? `#${m.product_id}`}
                    <Why text={m.explanation} />
                  </td>
                  <td className="text-right tabular-nums">{m.units_sold.toFixed(0)}</td>
                  <td className="text-right tabular-nums">{m.avg_sale_price.toFixed(2)} €</td>
                  <td className="text-right tabular-nums">{m.last_cost.toFixed(2)} €</td>
                  <td
                    className={`text-right font-semibold tabular-nums ${m.margin_unit < 0 ? "text-red-500" : ""}`}
                  >
                    {m.margin_unit.toFixed(2)} €
                  </td>
                  <td className="text-right tabular-nums">
                    {m.margin_pct != null ? `${(m.margin_pct * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td>
                    {m.cost_trend === "up" && (
                      <span className="pill bg-red-100 text-red-700" title={m.signal ?? ""}>
                        ↑ coût
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {(margins?.items.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-night/40 dark:text-surface/40">
                    Pas encore de ventes sur la période.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Charges OPEX/CAPEX */}
      <Card title="Charges (OPEX / CAPEX)" subtitle="Classez vos factures en un clic — validation humaine">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-night/[0.06] text-left text-night/50 dark:border-white/10 dark:text-surface/50">
                <th className="py-2">Facture</th>
                <th className="text-right">Montant</th>
                <th>Nature</th>
                <th>Catégorie</th>
                <th>Source</th>
                <th>Reclasser</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((inv) => (
                <tr key={inv.id} className="border-b border-night/[0.04] last:border-0 dark:border-white/[0.06]">
                  <td className="py-2 font-medium">
                    {inv.number ?? `#${inv.id}`}
                    {inv.classification_explanation && <Why text={inv.classification_explanation} />}
                  </td>
                  <td className="text-right tabular-nums">
                    {inv.total_amount != null ? `${inv.total_amount.toFixed(2)} €` : "—"}
                  </td>
                  <td>
                    <span className={`pill ${KIND_STYLE[inv.expense_kind] ?? KIND_STYLE.unknown}`}>
                      {inv.expense_kind}
                    </span>
                  </td>
                  <td className="text-night/70 dark:text-surface/70">{catLabel(inv.category_id)}</td>
                  <td>
                    {inv.classification_source && (
                      <span className="pill bg-night/5 text-night/60 dark:bg-white/10 dark:text-surface/60">
                        {inv.classification_source}
                        {inv.classification_confidence != null &&
                          ` ${(inv.classification_confidence * 100).toFixed(0)}%`}
                      </span>
                    )}
                  </td>
                  <td>
                    <select
                      value={inv.category_id ?? ""}
                      onChange={(e) => correct(inv, Number(e.target.value))}
                      className="rounded-card border border-night/10 bg-white px-2 py-1 text-xs dark:border-white/15 dark:bg-night dark:text-surface"
                    >
                      <option value="" disabled>
                        choisir…
                      </option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.label} ({c.kind})
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-night/40 dark:text-surface/40">
                    Aucune facture. Importez-en (Factures) puis classez-les.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
