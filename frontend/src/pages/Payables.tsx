import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import { getPayables, payInvoice, type PayablesView } from "../api/client";

/** Échéancier fournisseurs + trésorerie prévisionnelle (pilotage, human-in-the-loop). */
export default function Payables() {
  const [data, setData] = useState<PayablesView | null>(null);

  const load = useCallback(async () => setData(await getPayables()), []);
  useEffect(() => {
    void load();
  }, [load]);

  const pay = async (id: number) => {
    if (!confirm("Marquer cette facture comme payée ?")) return;
    await payInvoice(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Échéancier fournisseurs 💶</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Ce que vous devez, quand, et comment votre trésorerie évolue les 4 prochaines
          semaines. {data?.disclaimer}
        </p>
      </div>

      {data?.alert && (
        <div className="rounded-card border border-rose-500/30 bg-rose-500/5 p-4 text-sm font-medium text-rose-600 dark:text-rose-300">
          ⚠️ {data.alert}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Kpi label="Total à payer" value={`${(data?.total_due ?? 0).toFixed(0)} €`} />
        <Kpi
          label="En retard"
          value={`${(data?.overdue_amount ?? 0).toFixed(0)} €`}
          tone={data && data.overdue_amount > 0 ? "text-rose-600 dark:text-rose-400" : undefined}
        />
        <Kpi label="Solde estimé" value={`${(data?.opening_balance ?? 0).toFixed(0)} €`} />
      </div>

      {/* Projection hebdomadaire */}
      <Card title="Trésorerie prévisionnelle (4 semaines)" subtitle={data?.explanation}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-night/10 text-left text-night/50 dark:border-white/10 dark:text-surface/50">
              <th className="py-2">Semaine</th>
              <th className="text-right">Entrées est.</th>
              <th className="text-right">À payer</th>
              <th className="text-right">Net</th>
              <th className="text-right">Solde projeté</th>
            </tr>
          </thead>
          <tbody>
            {(data?.weeks ?? []).map((w) => (
              <tr
                key={w.week_start}
                className="border-b border-night/[0.06] last:border-0 dark:border-white/[0.06]"
              >
                <td className="py-2">{w.week_start}</td>
                <td className="text-right tabular-nums text-emerald-600 dark:text-emerald-400">
                  +{w.expected_inflow.toFixed(0)} €
                </td>
                <td className="text-right tabular-nums text-rose-600 dark:text-rose-400">
                  −{w.payables_due.toFixed(0)} €
                </td>
                <td className="text-right tabular-nums">{w.net.toFixed(0)} €</td>
                <td
                  className={`text-right font-semibold tabular-nums ${
                    w.running_balance < 0 ? "text-rose-600 dark:text-rose-400" : ""
                  }`}
                >
                  {w.running_balance.toFixed(0)} €
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Buckets par horizon */}
      {(data?.buckets ?? []).map((b) => (
        <Card key={b.key} title={`${b.label} · ${b.count} facture(s)`} subtitle={`${b.amount.toFixed(0)} €`}>
          <div className="space-y-2">
            {b.invoices.map((inv) => (
              <div
                key={inv.invoice_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-night/[0.06] p-3 dark:border-white/10"
              >
                <div className="min-w-0">
                  <span className="font-semibold">{inv.number ?? `#${inv.invoice_id}`}</span>
                  {inv.overdue && <Badge value="critical" />}
                  <span className="ml-2 text-xs text-night/50 dark:text-surface/50">
                    {inv.supplier_name ?? "—"}
                    {inv.due_date ? ` · échéance ${inv.due_date}` : " · sans échéance"}
                    {inv.days_to_due != null &&
                      (inv.days_to_due < 0
                        ? ` (${-inv.days_to_due} j de retard)`
                        : ` (dans ${inv.days_to_due} j)`)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold tabular-nums">{inv.amount.toFixed(2)} €</span>
                  <button
                    onClick={() => pay(inv.invoice_id)}
                    className="rounded-pill bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-300"
                  >
                    Marquer payée
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ))}

      {(data?.buckets ?? []).length === 0 && (
        <Card title="Aucune facture à payer">
          <p className="text-sm text-night/50 dark:text-surface/50">
            Tout est réglé. Votre trésorerie n'a pas d'échéance en attente. 👍
          </p>
        </Card>
      )}
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-card border border-night/[0.06] p-4 dark:border-white/10">
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className={`text-2xl font-bold tabular-nums ${tone ?? ""}`}>{value}</div>
    </div>
  );
}
