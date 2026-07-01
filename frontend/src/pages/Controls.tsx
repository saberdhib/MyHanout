import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { getInvoiceControls, getShrinkage } from "../api/client";

const KIND: Record<string, string> = {
  price_drift: "prix en hausse",
  price_vs_order: "prix ≠ commande",
  qty_vs_order: "quantité ≠ commande",
};

/** Contrôles & pertes : euros payés en trop (factures) + pertes invisibles (stock). */
export default function Controls() {
  const { data: invoices } = usePolling(() => getInvoiceControls(), 60000);
  const { data: shrink } = usePolling(() => getShrinkage(), 60000);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Contrôles & pertes 🔍</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Deux vérifications automatiques : ce que vous payez en trop, et ce qui disparaît.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Kpi
          label="Payé en trop (factures)"
          value={`${(invoices?.total_overcharge ?? 0).toFixed(0)} €`}
          sub={invoices ? `${invoices.invoices_checked} facture(s) contrôlée(s)` : "…"}
        />
        <Kpi
          label="Pertes invisibles (stock)"
          value={`${(shrink?.total_loss ?? 0).toFixed(0)} €`}
          sub={shrink ? `${shrink.products_checked} produit(s) contrôlé(s)` : "…"}
        />
      </div>

      <Card title="Contrôle des factures" subtitle={invoices?.explanation}>
        <div className="space-y-3">
          {(invoices?.findings ?? []).map((f, i) => (
            <div
              key={`${f.invoice_id}-${f.kind}-${i}`}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">
                  {f.product_name ?? `#${f.product_id}`} <Badge value={KIND[f.kind] ?? f.kind} />
                </div>
                <div className="text-sm font-bold text-amber-600 dark:text-amber-400">
                  ~{f.overcharge.toFixed(2)} €
                </div>
              </div>
              <div className="mt-1 text-xs text-night/50 dark:text-surface/50">
                {f.invoice_number}
                {f.supplier_name ? ` · ${f.supplier_name}` : ""}
              </div>
              <p className="mt-2 text-sm text-night/70 dark:text-surface/70">{f.explanation}</p>
            </div>
          ))}
          {(invoices?.findings ?? []).length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Aucun écart : vos factures collent à vos commandes et aux prix connus. 👍
            </p>
          )}
        </div>
      </Card>

      <Card title="Démarque inconnue (vol / casse / erreurs)" subtitle={shrink?.explanation}>
        <div className="space-y-3">
          {(shrink?.items ?? []).map((it) => (
            <div
              key={it.product_id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">{it.product_name ?? `#${it.product_id}`}</div>
                <div className="text-sm font-bold text-rose-600 dark:text-rose-400">
                  −{it.missing_units.toFixed(0)} unité(s) · ~{it.estimated_loss.toFixed(0)} €
                </div>
              </div>
              <div className="mt-1 text-xs text-night/50 dark:text-surface/50">
                attendu {it.expected_stock.toFixed(0)} · réel {it.actual_stock.toFixed(0)} · depuis
                le {it.baseline_date}
              </div>
              <p className="mt-2 text-sm text-night/70 dark:text-surface/70">{it.explanation}</p>
            </div>
          ))}
          {(shrink?.items ?? []).length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Aucune perte inexpliquée détectée. (Le cycle quotidien pose les inventaires de
              référence.)
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-card border border-night/[0.06] p-4 dark:border-white/10">
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs text-night/40 dark:text-surface/40">{sub}</div>}
    </div>
  );
}
