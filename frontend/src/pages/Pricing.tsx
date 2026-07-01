import { useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { applyPrice, getPriceSuggestions } from "../api/client";

const ACTION: Record<string, { label: string; cls: string }> = {
  raise: { label: "monter", cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300" },
  lower: { label: "baisser", cls: "bg-amber-500/15 text-amber-600 dark:text-amber-300" },
  hold: { label: "garder", cls: "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60" },
};

export default function Pricing() {
  const { data, refresh } = usePolling(() => getPriceSuggestions(), 30000);
  const [busy, setBusy] = useState<number | null>(null);

  async function apply(pid: number, price: number) {
    setBusy(pid);
    try {
      await applyPrice(pid, price);
      refresh();
    } finally {
      setBusy(null);
    }
  }

  const items = (data?.items ?? []).filter((p) => p.action !== "hold");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Prix conseillés 🎯</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Prix suggéré selon votre marge cible + arrondi psychologique. Vous décidez.
        </p>
      </div>

      <Card title={`${items.length} prix à revoir`} subtitle="Triés par ampleur d'ajustement">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-night/50 dark:text-surface/50">
                <th className="py-1">Produit</th>
                <th className="py-1">Actuel</th>
                <th className="py-1">Conseillé</th>
                <th className="py-1">Marge</th>
                <th className="py-1"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => {
                const a = ACTION[p.action] ?? ACTION.hold;
                return (
                  <tr
                    key={p.product_id}
                    className="border-t border-night/[0.06] align-top dark:border-white/10"
                  >
                    <td className="py-2">
                      <div className="font-semibold">
                        {p.product_name ?? `#${p.product_id}`} <Badge value={a.label} />
                      </div>
                      <div className="max-w-md text-xs text-night/50 dark:text-surface/50">
                        {p.explanation}
                      </div>
                    </td>
                    <td className="py-2">{p.current_price.toFixed(2)} €</td>
                    <td className="py-2 font-bold text-brand">{p.suggested_price.toFixed(2)} €</td>
                    <td className="py-2">
                      {(p.current_margin * 100).toFixed(0)}% → {(p.target_margin * 100).toFixed(0)}%
                    </td>
                    <td className="py-2">
                      <button
                        onClick={() => apply(p.product_id, p.suggested_price)}
                        disabled={busy === p.product_id}
                        className="rounded-card bg-brand px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      >
                        Appliquer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {items.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Vos prix tiennent la marge cible. 👍
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
