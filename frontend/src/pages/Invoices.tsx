import { useEffect, useRef, useState } from "react";
import { Card } from "../components/Card";
import {
  getInvoices,
  importInvoicesFromEmail,
  patchInvoice,
  uploadInvoice,
  type Invoice,
} from "../api/client";

// Factures : drag & drop / import, édition pré-remplie, bascule payé/non payé.
export default function Invoices() {
  const [rows, setRows] = useState<Invoice[]>([]);
  const [drag, setDrag] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = () => getInvoices().then((r) => setRows(r.items)).catch(() => setRows([]));
  useEffect(() => {
    refresh();
  }, []);

  async function upload(file: File) {
    setMsg(null);
    const inv = await uploadInvoice(file);
    setMsg(`Facture importée (#${inv.id}) — statut ${inv.status} (à valider).`);
    refresh();
  }

  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files[0]) await upload(e.dataTransfer.files[0]);
  }

  async function importEmail() {
    setMsg(null);
    const r = await importInvoicesFromEmail();
    setMsg(
      `📧 ${r.imported} facture(s) importée(s) depuis la boîte mail (${r.provider}) — à valider.`,
    );
    refresh();
  }

  async function togglePaid(inv: Invoice) {
    await patchInvoice(inv.id, { paid: !inv.paid });
    refresh();
  }

  async function editField(inv: Invoice, field: "number") {
    const value = prompt(`Nouveau ${field}`, inv[field] ?? "");
    if (value != null) {
      await patchInvoice(inv.id, { [field]: value });
      refresh();
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Factures</h1>
        <button
          onClick={importEmail}
          className="rounded-card bg-brand px-3 py-1 text-sm text-white"
        >
          📧 Importer depuis l'email
        </button>
      </div>

      {/* Zone drag & drop + import fichier */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        className={`cursor-pointer rounded-card border-2 border-dashed p-8 text-center text-sm ${
          drag ? "border-brand bg-brand/5" : "border-gray-300 dark:border-white/15"
        }`}
      >
        📥 Glissez-déposez une facture (PDF/photo) ou cliquez pour importer —
        l'IA pré-remplit n°, date, fournisseur (validation humaine ensuite).
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
        />
      </div>
      {msg && <div className="rounded-card bg-green-50 p-3 text-sm text-green-800">{msg}</div>}

      <Card>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2">Numéro</th>
              <th>Échéance</th>
              <th>Montant</th>
              <th>Statut</th>
              <th>Payé</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((inv) => (
              <tr key={inv.id} className="border-b last:border-0">
                <td className="py-2">
                  <button onClick={() => editField(inv, "number")} className="underline-offset-2 hover:underline">
                    {inv.number ?? "— éditer"}
                  </button>
                </td>
                <td>{inv.due_date ?? "—"}</td>
                <td>
                  {inv.total_amount != null ? `${inv.total_amount.toFixed(2)} ${inv.currency}` : "—"}
                </td>
                <td>{inv.status}</td>
                <td>
                  <button
                    onClick={() => togglePaid(inv)}
                    className={`rounded-pill px-2 py-0.5 text-xs ${
                      inv.paid ? "bg-green-100 text-green-700" : "bg-accent/20 text-accent"
                    }`}
                  >
                    {inv.paid ? "✓ Payé" : "À payer"}
                  </button>
                </td>
                <td className="text-xs text-gray-400">{inv.lines.length} ligne(s)</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-center text-gray-400">
                  Aucune facture. Importez-en une ci-dessus.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
