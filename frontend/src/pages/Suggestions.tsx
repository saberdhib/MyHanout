import { useState } from "react";
import { Card } from "../components/Card";
import { confirmOrder, getSuggestion, type Suggestion } from "../api/client";

export default function Suggestions() {
  const [horizon, setHorizon] = useState("demain");
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [confirmed, setConfirmed] = useState<string | null>(null);

  async function fetchSuggestion() {
    setConfirmed(null);
    const s = await getSuggestion(horizon);
    setSuggestion(s);
    setQty(Object.fromEntries(s.lines.map((l) => [l.product_id, l.suggested_quantity])));
  }

  async function confirm(mode: string) {
    if (!suggestion) return;
    const lines = suggestion.lines.map((l) => ({
      product_id: l.product_id,
      quantity: qty[l.product_id] ?? l.suggested_quantity,
    }));
    const order = await confirmOrder(lines, mode);
    setConfirmed(`Commande #${order.id} (${order.action_mode}) — ${order.status}`);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Suggestions de commande</h1>
      <div className="flex items-center gap-2">
        <select
          value={horizon}
          onChange={(e) => setHorizon(e.target.value)}
          className="rounded border px-2 py-1 text-sm"
        >
          <option value="demain">Demain</option>
          <option value="semaine">Semaine prochaine</option>
        </select>
        <button
          onClick={fetchSuggestion}
          className="rounded bg-brand px-3 py-1 text-sm text-white"
        >
          Proposer une commande
        </button>
      </div>

      {confirmed && (
        <div className="rounded bg-green-50 p-3 text-sm text-green-800">{confirmed}</div>
      )}

      {suggestion && (
        <Card title={`Modèle ${suggestion.model} · horizon ${suggestion.horizon_days} j`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2">Produit</th>
                <th>Suggéré</th>
                <th>Ajuster</th>
                <th>Pourquoi (explicabilité)</th>
                <th>Confiance</th>
              </tr>
            </thead>
            <tbody>
              {suggestion.lines.map((l) => (
                <tr key={l.product_id} className="border-b align-top last:border-0">
                  <td className="py-2">{l.product_name}</td>
                  <td>
                    {l.suggested_quantity} {l.unit}
                  </td>
                  <td>
                    <input
                      type="number"
                      className="w-20 rounded border px-1 py-0.5"
                      value={qty[l.product_id] ?? l.suggested_quantity}
                      onChange={(e) =>
                        setQty({ ...qty, [l.product_id]: Number(e.target.value) })
                      }
                    />
                  </td>
                  <td className="max-w-md text-xs text-gray-600">{l.explanation}</td>
                  <td>{(l.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
              {suggestion.lines.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-gray-400">
                    Aucune commande nécessaire (stocks suffisants).
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {suggestion.lines.length > 0 && (
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => confirm("whatsapp_auto")}
                className="rounded bg-brand px-3 py-1 text-sm text-white"
              >
                Envoyer au fournisseur (WhatsApp)
              </button>
              <button
                onClick={() => confirm("draft")}
                className="rounded border px-3 py-1 text-sm"
              >
                Générer un brouillon
              </button>
              <button
                onClick={() => confirm("record_only")}
                className="rounded border px-3 py-1 text-sm"
              >
                Enregistrer seulement
              </button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
