import { useState } from "react";
import { Card } from "../components/Card";
import { importJson, syncDwh, type DwhSyncResult, type ImportResult } from "../api/client";

const SAMPLE = JSON.stringify(
  {
    suppliers: [{ name: "Primeur Local", email: "contact@primeur.fr", lead_time_days: 1 }],
    products: [
      {
        sku: "TOMATE",
        name: "Tomate grappe",
        unit: "kg",
        unit_price: 2.4,
        category: "légumes",
        perishable: true,
        supplier_name: "Primeur Local",
        stock_quantity: 18,
        reorder_threshold: 10,
      },
    ],
    sales: [{ sku: "TOMATE", quantity: 6, unit_price: 2.4, sold_at: "2026-06-28T10:00:00Z" }],
  },
  null,
  2,
);

// Intégrations : import JSON (caisse/ERP/tableur) + synchronisation DWH.
export default function Integrations() {
  const [raw, setRaw] = useState(SAMPLE);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [dwh, setDwh] = useState<DwhSyncResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function runImport() {
    setErr(null);
    setResult(null);
    try {
      const payload = JSON.parse(raw);
      setResult(await importJson(payload));
    } catch (e) {
      setErr(e instanceof SyntaxError ? "JSON invalide." : "Échec de l'import.");
    }
  }

  async function runSync() {
    setDwh(null);
    setDwh(await syncDwh());
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Intégrations</h1>
      <p className="text-sm text-gray-500">
        Importez votre catalogue/ventes depuis un export (caisse, ERP, tableur) au format JSON,
        ou synchronisez un snapshot vers votre entrepôt de données. Idempotent par SKU.
      </p>

      <Card title="Import JSON">
        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          spellCheck={false}
          className="h-64 w-full rounded-card border border-gray-300 bg-white p-3 font-mono text-xs dark:border-white/15 dark:bg-night dark:text-surface"
        />
        <div className="mt-3 flex items-center gap-3">
          <button onClick={runImport} className="rounded-card bg-brand px-3 py-1 text-sm text-white">
            Importer
          </button>
          {err && <span className="text-sm text-red-600">{err}</span>}
        </div>
        {result && (
          <div className="mt-3 rounded-card bg-green-50 p-3 text-sm text-green-800">
            ✅ {result.suppliers_upserted} fournisseur(s), {result.products_upserted} produit(s),{" "}
            {result.stocks_upserted} stock(s), {result.sales_inserted} vente(s).
          </div>
        )}
      </Card>

      <Card title="Synchronisation entrepôt de données (DWH)">
        <p className="text-sm text-gray-500">
          Pousse un snapshot (catalogue + stock + ventes) vers la cible configurée. En mode
          mock (keyless), rien ne quitte le système : le snapshot est journalisé localement.
        </p>
        <button
          onClick={runSync}
          className="mt-3 rounded-card border border-brand px-3 py-1 text-sm text-brand"
        >
          Synchroniser maintenant
        </button>
        {dwh && (
          <div className="mt-3 rounded-card bg-green-50 p-3 text-sm text-green-800">
            ✅ {dwh.rows} ligne(s) → cible « {dwh.target} »{dwh.detail ? ` — ${dwh.detail}` : ""}.
          </div>
        )}
      </Card>
    </div>
  );
}
