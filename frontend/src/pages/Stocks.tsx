import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { getStocks, type Stock } from "../api/client";

export default function Stocks() {
  const [rows, setRows] = useState<Stock[]>([]);

  useEffect(() => {
    getStocks().then((r) => setRows(r.items)).catch(() => setRows([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Stocks</h1>
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2">Produit</th>
              <th>SKU</th>
              <th>Quantité</th>
              <th>Seuil</th>
              <th>Péremption</th>
              <th>État</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="border-b last:border-0">
                <td className="py-2">{s.product_name ?? "—"}</td>
                <td>{s.product_sku ?? "—"}</td>
                <td>{s.quantity}</td>
                <td>{s.reorder_threshold}</td>
                <td>{s.expiry_date ?? "—"}</td>
                <td>
                  {s.low_stock ? (
                    <span className="rounded bg-red-100 px-2 py-0.5 text-red-700">
                      Rupture
                    </span>
                  ) : (
                    <span className="rounded bg-green-100 px-2 py-0.5 text-green-700">
                      OK
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-center text-gray-400">
                  Aucune donnée. Chargez les seeds (make seed).
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
