import { useCallback } from "react";
import { Card, Stat } from "../components/Card";
import { Badge, Gauge } from "../components/Charts";
import {
  getAlerts,
  getInvoices,
  getMlopsMetrics,
  getPipelineHealth,
  getRecommendations,
  getSignals,
  getStockAlerts,
  getStocks,
} from "../api/client";
import { usePolling } from "../hooks/usePolling";
import { useEventStream } from "../hooks/useEventStream";

async function loadSummary() {
  const [s, a, i, m, sig, recs, alerts, health] = await Promise.all([
    getStocks(),
    getStockAlerts(),
    getInvoices(),
    getMlopsMetrics(),
    getSignals(),
    getRecommendations(),
    getAlerts("open"),
    getPipelineHealth(),
  ]);
  const mape =
    m.length && m.some((x) => x.mape != null)
      ? (m.reduce((acc, x) => acc + (x.mape ?? 0), 0) / m.length) * 100
      : null;
  const daily = health.jobs.find((j) => j.job_name === "daily");
  return {
    stocks: s.total,
    alerts: a.total,
    invoices: i.total,
    mape,
    signals: sig,
    recs: recs.items,
    openAlerts: alerts.items,
    freshness: daily?.data_freshness_at ?? null,
  };
}

export default function Dashboard() {
  const { data, error, refresh } = usePolling(loadSummary, 10000);
  const onEvent = useCallback(
    (e: { type: string }) => {
      if (
        ["forecast_ready", "alert_created", "alert_resolved", "pipeline_finished", "inventory_updated"].includes(
          e.type,
        )
      )
        refresh();
    },
    [refresh],
  );
  const { connected } = useEventStream(onEvent);

  const orders = (data?.recs ?? []).filter((r) => r.action === "order").slice(0, 5);
  const topAlerts = (data?.openAlerts ?? []).slice(0, 5);

  function fresh(iso: string | null): string {
    if (!iso) return "—";
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    return mins < 60 ? `${mins} min` : `${Math.round(mins / 60)} h`;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">Tableau de bord</h1>
          <p className="page-sub">Vue décisionnelle de votre commerce, en temps réel.</p>
        </div>
        <span className="pill bg-brand/10 text-brand-dark dark:text-brand-light">
          {connected ? "● temps réel (SSE)" : "⟳ live · 10s"}
        </span>
      </div>
      {error && (
        <div className="rounded-card bg-red-50 p-3 text-sm text-red-700">
          API injoignable. Lancez le backend (docker compose up).
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Recommandations" value={data?.recs.length ?? "—"} icon="🧠" />
        <Stat label="Alertes ouvertes" value={data?.alerts ?? "—"} icon="🔔" />
        <Stat
          label="MAPE (qualité prévision)"
          value={data?.mape != null ? `${data.mape.toFixed(1)}%` : "—"}
          icon="🎯"
        />
        <Stat
          label="Fraîcheur données"
          value={data ? fresh(data.freshness) : "—"}
          icon="🗄️"
          hint="dernier pipeline « daily »"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Réassort prioritaire" subtitle="Top recommandations à commander">
          <div className="space-y-3">
            {orders.map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">
                    {r.product_name ?? `Produit #${r.product_id}`}{" "}
                    <span className="text-night/50 dark:text-surface/50">
                      · {r.suggested_quantity.toFixed(0)} u
                    </span>
                  </div>
                  <div className="mt-1 w-40">
                    <Gauge value={r.risk_factor} danger />
                  </div>
                </div>
                <Badge value={r.action} />
              </div>
            ))}
            {orders.length === 0 && (
              <p className="py-3 text-sm text-night/40 dark:text-surface/40">
                Rien d'urgent : stocks suffisants. 🎉
              </p>
            )}
          </div>
        </Card>

        <Card title="Top risques (alertes)" subtitle="Ruptures / péremptions à traiter">
          <div className="space-y-2">
            {topAlerts.map((a) => (
              <div key={a.id} className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate">{a.title}</span>
                <Badge value={a.priority} />
              </div>
            ))}
            {topAlerts.length === 0 && (
              <p className="py-3 text-sm text-night/40 dark:text-surface/40">Aucune alerte ouverte.</p>
            )}
          </div>
        </Card>
      </div>

      {data?.signals && (
        <Card title="Signaux du jour (compagnon)">
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="rounded-pill bg-accent/15 px-3 py-1">
              ☀️ {data.signals.weather.temp_c}°C · {data.signals.weather.condition} —{" "}
              {data.signals.weather.demand_hint}
            </span>
            {data.signals.trends.map((t) => (
              <span key={t.topic} className="rounded-pill bg-brand/15 px-3 py-1">
                📈 {t.topic} — {t.hint}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
