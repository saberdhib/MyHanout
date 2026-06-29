import { Card, Stat } from "../components/Card";
import { getInvoices, getMlopsMetrics, getStockAlerts, getStocks } from "../api/client";
import { usePolling } from "../hooks/usePolling";

async function loadSummary() {
  const [s, a, i, m] = await Promise.all([
    getStocks(),
    getStockAlerts(),
    getInvoices(),
    getMlopsMetrics(),
  ]);
  const mape =
    m.length && m.some((x) => x.mape != null)
      ? (m.reduce((acc, x) => acc + (x.mape ?? 0), 0) / m.length) * 100
      : null;
  return { stocks: s.total, alerts: a.total, invoices: i.total, mape };
}

export default function Dashboard() {
  // Dashboard live : rafraîchissement par polling (couche temps-réel isolée).
  const { data, error } = usePolling(loadSummary, 10000);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        <span className="text-xs text-gray-400">⟳ live (10s)</span>
      </div>
      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          API injoignable. Lancez le backend (docker compose up).
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Stat label="Références en stock" value={data?.stocks ?? "—"} />
        <Stat label="Alertes stock" value={data?.alerts ?? "—"} />
        <Stat label="Factures" value={data?.invoices ?? "—"} />
        <Stat
          label="MAPE moyen (qualité prévision)"
          value={data?.mape != null ? `${data.mape.toFixed(1)}%` : "—"}
        />
      </div>
      <Card title="Boucle quotidienne">
        <p className="text-sm text-gray-600">
          Consultez vos stocks et prévisions, recevez des suggestions de commande
          explicables, saisissez votre fin de journée, et suivez l'écart prévu/réel.
          Les actions sensibles (commandes) requièrent une validation humaine.
        </p>
      </Card>
    </div>
  );
}
