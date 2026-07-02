import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { getBacktest, getForecast, type BacktestReport, type Forecast } from "../api/client";

export default function Forecasts() {
  const [productId, setProductId] = useState(1);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backtest, setBacktest] = useState<BacktestReport | null>(null);

  useEffect(() => {
    getForecast(productId, 14)
      .then((f) => {
        setForecast(f);
        setError(null);
      })
      .catch(() => setError("Aucune prévision (produit inexistant ou pas d'historique)."));
    getBacktest(productId)
      .then(setBacktest)
      .catch(() => setBacktest(null));
  }, [productId]);

  const max = forecast
    ? Math.max(...forecast.points.map((p) => p.yhat), 1)
    : 1;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Prévisions de demande</h1>
      <div className="flex items-center gap-2">
        <label className="text-sm text-gray-600">Produit ID :</label>
        <input
          type="number"
          min={1}
          value={productId}
          onChange={(e) => setProductId(Number(e.target.value))}
          className="w-24 rounded border px-2 py-1 text-sm"
        />
      </div>
      {error && (
        <div className="rounded bg-yellow-50 p-3 text-sm text-yellow-800">{error}</div>
      )}
      {forecast && (
        <Card title={`Modèle : ${forecast.model} (${forecast.horizon_days} j)`}>
          <p className="mb-4 text-sm text-gray-500">{forecast.explanation}</p>
          <div className="flex items-end gap-1" style={{ height: 160 }}>
            {forecast.points.map((p) => (
              <div key={p.ds} className="flex flex-1 flex-col items-center justify-end">
                <div
                  className="w-full rounded-t bg-brand"
                  style={{ height: `${(p.yhat / max) * 140}px` }}
                  title={`${p.ds}: ${p.yhat}`}
                />
                <span className="mt-1 text-[10px] text-gray-400">
                  {p.ds.slice(5)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {backtest && (
        <Card title="Backtest — quel modèle est le meilleur ?" subtitle={backtest.verdict}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-night/10 text-left text-night/50 dark:border-white/10 dark:text-surface/50">
                <th className="py-2">Modèle</th>
                <th className="text-right">MAPE (erreur %)</th>
                <th className="text-right">MAE</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {backtest.results.map((r) => (
                <tr
                  key={r.model}
                  className={`border-b border-night/[0.06] last:border-0 dark:border-white/[0.06] ${
                    r.model === backtest.best_model ? "font-semibold" : ""
                  }`}
                >
                  <td className="py-2">
                    {r.model === "mean" ? "moyenne plate" : r.model}
                    {r.model === backtest.best_model && " ✅"}
                  </td>
                  <td className="text-right tabular-nums">
                    {r.mape != null ? `${(r.mape * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td className="text-right tabular-nums">{r.mae != null ? r.mae.toFixed(2) : "—"}</td>
                  <td className="text-xs text-night/50 dark:text-surface/50">
                    {r.available ? `${r.n_points} pts` : "non installé"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
