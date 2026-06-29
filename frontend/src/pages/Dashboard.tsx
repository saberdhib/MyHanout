import { useEffect, useState } from "react";
import { Card, Stat } from "../components/Card";
import { getInvoices, getStockAlerts, getStocks } from "../api/client";

export default function Dashboard() {
  const [stocks, setStocks] = useState(0);
  const [alerts, setAlerts] = useState(0);
  const [invoices, setInvoices] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStocks(), getStockAlerts(), getInvoices()])
      .then(([s, a, i]) => {
        setStocks(s.total);
        setAlerts(a.total);
        setInvoices(i.total);
      })
      .catch(() => setError("API injoignable. Lancez le backend (docker compose up)."));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tableau de bord</h1>
      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Références en stock" value={stocks} />
        <Stat label="Alertes stock" value={alerts} />
        <Stat label="Factures" value={invoices} />
      </div>
      <Card title="Bienvenue">
        <p className="text-sm text-gray-600">
          MyHanout AI — copilot des commerces de proximité. Consultez vos stocks,
          prévisions de demande et factures. Les actions sensibles (commandes)
          requièrent une validation humaine.
        </p>
      </Card>
    </div>
  );
}
