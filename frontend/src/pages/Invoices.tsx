import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { getInvoices, type Invoice } from "../api/client";

export default function Invoices() {
  const [rows, setRows] = useState<Invoice[]>([]);

  useEffect(() => {
    getInvoices().then((r) => setRows(r.items)).catch(() => setRows([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Factures</h1>
      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2">Numéro</th>
              <th>Échéance</th>
              <th>Montant</th>
              <th>Statut</th>
              <th>OCR</th>
              <th>Lignes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((inv) => (
              <tr key={inv.id} className="border-b last:border-0">
                <td className="py-2">{inv.number ?? "—"}</td>
                <td>{inv.due_date ?? "—"}</td>
                <td>
                  {inv.total_amount != null
                    ? `${inv.total_amount.toFixed(2)} ${inv.currency}`
                    : "—"}
                </td>
                <td>{inv.status}</td>
                <td>{inv.ocr_status}</td>
                <td>{inv.lines.length}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-center text-gray-400">
                  Aucune facture. Chargez les seeds (make seed).
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
