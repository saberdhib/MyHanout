import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { getForecast, type Forecast } from "../api/client";

export default function Forecasts() {
  const [productId, setProductId] = useState(1);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getForecast(productId, 14)
      .then((f) => {
        setForecast(f);
        setError(null);
      })
      .catch(() => setError("Aucune prévision (produit inexistant ou pas d'historique)."));
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
    </div>
  );
}
