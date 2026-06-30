import { useCallback, useState } from "react";
import { Card } from "../components/Card";
import { Badge, Gauge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { useEventStream } from "../hooks/useEventStream";
import { applyMarkdown, getMarkdowns, rejectMarkdown, scanMarkdowns } from "../api/client";

export default function Markdown() {
  const { data, refresh } = usePolling(() => getMarkdowns(), 15000);
  const [busy, setBusy] = useState(false);

  // Temps réel : un pipeline terminé peut générer de nouvelles démarques.
  const onEvent = useCallback(
    (e: { type: string }) => {
      if (e.type === "pipeline_finished") refresh();
    },
    [refresh],
  );
  const { connected } = useEventStream(onEvent);

  async function scan() {
    setBusy(true);
    try {
      await scanMarkdowns();
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function act(id: number, fn: (id: number) => Promise<unknown>) {
    await fn(id);
    refresh();
  }

  const items = (data?.items ?? []).filter((m) => m.status === "suggested");
  const totalRecovered = items.reduce((s, m) => s + m.recovered_value, 0);
  const totalRisk = items.reduce((s, m) => s + m.baseline_loss, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Démarque anti-gaspi 🏷️</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Écouler le frais avant péremption en récupérant un maximum de valeur.{" "}
            <span className={connected ? "text-emerald-600" : "text-night/40"}>
              ● {connected ? "temps réel" : "polling"}
            </span>
          </p>
        </div>
        <button
          onClick={scan}
          disabled={busy}
          className="rounded-card bg-brand px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Analyse…" : "Analyser les lots frais"}
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Kpi label="Lots à risque" value={`${items.length}`} />
        <Kpi label="Valeur récupérable" value={`${totalRecovered.toFixed(0)} €`} accent />
        <Kpi label="Perte évitée (sinon jetée)" value={`${totalRisk.toFixed(0)} €`} />
      </div>

      <Card title={`${items.length} démarque(s) suggérée(s)`} subtitle="Triées par priorité (perte évitée)">
        <div className="space-y-3">
          {items.map((m) => (
            <div
              key={m.id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">
                  {m.product_name ?? `Produit #${m.product_id}`}{" "}
                  <Badge value={`-${m.discount_pct}%`} />
                </div>
                <div className="text-sm text-night/50 dark:text-surface/50">
                  périme dans {m.days_to_expiry} j
                  {m.expiry_date ? ` · ${m.expiry_date}` : ""}
                </div>
              </div>

              <div className="mt-2 grid gap-3 sm:grid-cols-4">
                <Metric
                  label="Prix"
                  value={`${m.current_price.toFixed(2)} → ${m.suggested_price.toFixed(2)} €`}
                />
                <Metric label="Lot à risque" value={`${m.quantity_at_risk.toFixed(0)}`} />
                <Metric label="Valeur récupérée" value={`~${m.recovered_value.toFixed(0)} €`} />
                <div>
                  <div className="text-xs text-night/50 dark:text-surface/50">
                    Confiance {(m.confidence * 100).toFixed(0)}%
                  </div>
                  <Gauge value={m.confidence} />
                </div>
              </div>

              <p className="mt-2 text-sm text-night/70 dark:text-surface/70">{m.explanation}</p>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  onClick={() => act(m.id, applyMarkdown)}
                  className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white"
                >
                  Appliquer la démarque
                </button>
                <button
                  onClick={() => act(m.id, rejectMarkdown)}
                  className="rounded-card border border-night/15 px-3 py-1.5 text-sm dark:border-white/15"
                >
                  Ignorer
                </button>
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Aucun lot frais à risque. Lance « Analyser les lots frais ».
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
      <div className="text-base font-bold">{value}</div>
    </div>
  );
}

function Kpi({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-card border border-night/[0.06] p-4 dark:border-white/10">
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className={`text-2xl font-bold ${accent ? "text-brand" : ""}`}>{value}</div>
    </div>
  );
}
