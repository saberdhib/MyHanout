import { Card } from "../components/Card";
import { getMlopsMetrics, type MlopsMetric } from "../api/client";
import { usePolling } from "../hooks/usePolling";

// Écarts prévu/réel (boucle MLOps) — vue live.
export default function Quality() {
  const { data, error } = usePolling<MlopsMetric[]>(getMlopsMetrics, 15000);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Qualité des prévisions (écarts)</h1>
        <span className="text-xs text-gray-400">⟳ live (15s)</span>
      </div>
      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">API injoignable.</div>
      )}
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2">Produit</th>
              <th>Modèle</th>
              <th>N éval.</th>
              <th>MAE</th>
              <th>MAPE</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((m) => (
              <tr key={`${m.product_id}-${m.model}`} className="border-b last:border-0">
                <td className="py-2">#{m.product_id}</td>
                <td>{m.model}</td>
                <td>{m.n}</td>
                <td>{m.mae ?? "—"}</td>
                <td>{m.mape != null ? `${(m.mape * 100).toFixed(1)}%` : "—"}</td>
              </tr>
            ))}
            {(!data || data.length === 0) && (
              <tr>
                <td colSpan={5} className="py-4 text-center text-gray-400">
                  Aucune évaluation encore. Saisissez vos fins de journée pour
                  alimenter la boucle.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
