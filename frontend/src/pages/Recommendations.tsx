import { useCallback, useState } from "react";
import { Card } from "../components/Card";
import { Badge, Gauge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { useEventStream } from "../hooks/useEventStream";
import {
  getRecommendations,
  recomputeForecasts,
  simulateOrder,
  type Recommendation,
  type SimulateResult,
} from "../api/client";

export default function Recommendations() {
  const { data, refresh } = usePolling(() => getRecommendations(), 15000);
  const [busy, setBusy] = useState(false);
  const [sim, setSim] = useState<Record<number, SimulateResult>>({});
  const [simQty, setSimQty] = useState<Record<number, number>>({});

  // Temps réel : un nouveau calcul de forecast rafraîchit la liste sans reload.
  const onEvent = useCallback(
    (e: { type: string }) => {
      if (e.type === "forecast_ready" || e.type === "pipeline_finished") refresh();
    },
    [refresh],
  );
  const { connected } = useEventStream(onEvent);

  async function recompute() {
    setBusy(true);
    try {
      await recomputeForecasts();
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function runSim(r: Recommendation) {
    const qty = simQty[r.product_id] ?? Math.round(r.suggested_quantity);
    const res = await simulateOrder(r.product_id, qty, r.horizon_days);
    setSim({ ...sim, [r.product_id]: res });
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Recommandations</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Réassort explicable, croisant prévision + stock + signaux métier.{" "}
            <span className={connected ? "text-emerald-600" : "text-night/40"}>
              ● {connected ? "temps réel" : "polling"}
            </span>
          </p>
        </div>
        <button
          onClick={recompute}
          disabled={busy}
          className="rounded-card bg-brand px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Calcul…" : "Recalculer"}
        </button>
      </div>

      <Card title={`${items.length} recommandation(s)`} subtitle="Triées par priorité (score)">
        <div className="space-y-3">
          {items.map((r) => (
            <div
              key={r.id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">
                  {r.product_name ?? `Produit #${r.product_id}`} <Badge value={r.action} />
                </div>
                <div className="text-sm text-night/50 dark:text-surface/50">
                  modèle {r.model_version}
                  {r.pipeline_run_id ? ` · run #${r.pipeline_run_id}` : ""}
                </div>
              </div>
              <div className="mt-2 grid gap-3 sm:grid-cols-3">
                <Metric label="Quantité suggérée" value={`${r.suggested_quantity.toFixed(0)}`} />
                <div>
                  <div className="text-xs text-night/50 dark:text-surface/50">
                    Risque de rupture {(r.risk_factor * 100).toFixed(0)}%
                  </div>
                  <Gauge value={r.risk_factor} danger />
                </div>
                <div>
                  <div className="text-xs text-night/50 dark:text-surface/50">
                    Confiance {(r.confidence * 100).toFixed(0)}%
                  </div>
                  <Gauge value={r.confidence} />
                </div>
              </div>
              <p className="mt-2 text-sm text-night/70 dark:text-surface/70">{r.explanation}</p>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <input
                  type="number"
                  className="w-24 rounded-card border border-night/10 px-2 py-1 text-sm dark:border-white/10 dark:bg-white/5"
                  placeholder="qté"
                  value={simQty[r.product_id] ?? Math.round(r.suggested_quantity)}
                  onChange={(e) =>
                    setSimQty({ ...simQty, [r.product_id]: Number(e.target.value) })
                  }
                />
                <button
                  onClick={() => runSim(r)}
                  className="rounded-card border border-night/15 px-3 py-1 text-sm dark:border-white/15"
                >
                  Simuler « et si je commande X ? »
                </button>
                {sim[r.product_id] && (
                  <span className="text-xs text-night/60 dark:text-surface/60">
                    {sim[r.product_id].explanation}
                  </span>
                )}
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Aucune recommandation. Lance « Recalculer » ou un pipeline depuis Data Ops.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}
