import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { createDailyEntry, getStocks, type Stock } from "../api/client";

// Saisie de fin de journée — pensée mobile, frictionless.
export default function EndOfDay() {
  const [rows, setRows] = useState<Stock[]>([]);
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState<Record<number, { ordered: number; remaining: number }>>({});
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    getStocks().then((r) => setRows(r.items)).catch(() => setRows([]));
  }, []);

  async function save(productId: number) {
    const f = form[productId] || { ordered: 0, remaining: 0 };
    await createDailyEntry({
      product_id: productId,
      entry_date: today,
      quantity_ordered: f.ordered,
      stock_remaining: f.remaining,
    });
    setSaved(`Saisie enregistrée (produit #${productId}).`);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Fin de journée — {today}</h1>
      <p className="text-sm text-gray-600">
        Déclarez, par produit, ce que vous avez commandé et ce qu'il vous reste.
        Cette saisie nourrit les prévisions (boucle d'apprentissage).
      </p>
      {saved && <div className="rounded bg-green-50 p-3 text-sm text-green-800">{saved}</div>}
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2">Produit</th>
              <th>Commandé</th>
              <th>Stock restant</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.product_id} className="border-b last:border-0">
                <td className="py-2">{s.product_name}</td>
                <td>
                  <input
                    type="number"
                    className="w-24 rounded border px-1 py-0.5"
                    onChange={(e) =>
                      setForm({
                        ...form,
                        [s.product_id]: {
                          ...(form[s.product_id] || { ordered: 0, remaining: 0 }),
                          ordered: Number(e.target.value),
                        },
                      })
                    }
                  />
                </td>
                <td>
                  <input
                    type="number"
                    className="w-24 rounded border px-1 py-0.5"
                    onChange={(e) =>
                      setForm({
                        ...form,
                        [s.product_id]: {
                          ...(form[s.product_id] || { ordered: 0, remaining: 0 }),
                          remaining: Number(e.target.value),
                        },
                      })
                    }
                  />
                </td>
                <td>
                  <button
                    onClick={() => save(s.product_id)}
                    className="rounded bg-brand px-3 py-1 text-xs text-white"
                  >
                    Enregistrer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
