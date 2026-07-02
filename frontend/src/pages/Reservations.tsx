import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import {
  createReservation,
  getCustomers,
  getProducts,
  getReservations,
  setReservationStatus,
  type CatalogProduct,
  type Customer,
  type Reservation,
} from "../api/client";

const STATUS_TONE: Record<string, string> = {
  pending: "high",
  confirmed: "medium",
  ready: "success",
  collected: "low",
  cancelled: "dismissed",
};
// Prochaine étape du cycle (bouton d'avancement).
const NEXT: Record<string, string> = {
  pending: "confirmed",
  confirmed: "ready",
  ready: "collected",
};
const NEXT_LABEL: Record<string, string> = {
  confirmed: "Valider",
  ready: "Marquer prête",
  collected: "Récupérée",
};

/** Réservations client (click & collect) : cycle demande → validée → prête → récupérée. */
export default function Reservations() {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    customer_id: "",
    customer_name: "",
    pickup_date: "",
    product_id: "",
    quantity: "1",
  });

  const load = useCallback(async () => {
    const [r, c, p] = await Promise.all([
      getReservations(),
      getCustomers(),
      getProducts(),
    ]);
    setReservations(r.items);
    setCustomers(c.items);
    setProducts(p.items);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const advance = async (id: number, status: string) => {
    await setReservationStatus(id, status);
    await load();
  };

  const submit = async () => {
    if (!form.product_id) return;
    await createReservation({
      customer_id: form.customer_id ? Number(form.customer_id) : undefined,
      customer_name: form.customer_name || undefined,
      pickup_date: form.pickup_date || undefined,
      lines: [{ product_id: Number(form.product_id), quantity: Number(form.quantity) || 1 }],
    });
    setForm({ customer_id: "", customer_name: "", pickup_date: "", product_id: "", quantity: "1" });
    setOpen(false);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Réservations 🛍️</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Click &amp; collect : le client réserve, vous préparez. Points de fidélité crédités
            à la récupération.
          </p>
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white"
        >
          {open ? "Fermer" : "Nouvelle réservation"}
        </button>
      </div>

      {open && (
        <Card title="Nouvelle réservation">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs text-night/50 dark:text-surface/50">Client connu</label>
              <select
                value={form.customer_id}
                onChange={(e) => setForm((f) => ({ ...f, customer_id: e.target.value }))}
                className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
              >
                <option value="">— de passage —</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name ?? `Client #${c.id}`}
                  </option>
                ))}
              </select>
            </div>
            <Field
              label="Nom (si de passage)"
              value={form.customer_name}
              onChange={(v) => setForm((f) => ({ ...f, customer_name: v }))}
            />
            <div>
              <label className="text-xs text-night/50 dark:text-surface/50">Produit</label>
              <select
                value={form.product_id}
                onChange={(e) => setForm((f) => ({ ...f, product_id: e.target.value }))}
                className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
              >
                <option value="">— choisir —</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.unit_price ?? 0} €)
                  </option>
                ))}
              </select>
            </div>
            <Field
              label="Quantité"
              type="number"
              value={form.quantity}
              onChange={(v) => setForm((f) => ({ ...f, quantity: v }))}
            />
            <Field
              label="Date de retrait"
              type="date"
              value={form.pickup_date}
              onChange={(v) => setForm((f) => ({ ...f, pickup_date: v }))}
            />
          </div>
          <button
            disabled={!form.product_id}
            onClick={submit}
            className="mt-3 rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            Créer la réservation
          </button>
        </Card>
      )}

      <Card title="Réservations" subtitle={`${reservations.length} au total`}>
        <div className="space-y-2">
          {reservations.map((r) => (
            <div
              key={r.id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <span className="font-semibold">
                    #{r.id} · {r.customer_name ?? (r.customer_id ? `Client #${r.customer_id}` : "—")}
                  </span>
                  <Badge value={STATUS_TONE[r.status] ?? "low"} />
                  <span className="ml-1 text-xs text-night/45 dark:text-surface/45">{r.status}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold tabular-nums">
                    {r.total_amount.toFixed(2)} €
                  </span>
                  {NEXT[r.status] && (
                    <button
                      onClick={() => advance(r.id, NEXT[r.status])}
                      className="rounded-pill bg-brand/10 px-3 py-1 text-xs font-semibold text-brand-dark dark:text-brand-light"
                    >
                      {NEXT_LABEL[NEXT[r.status]]}
                    </button>
                  )}
                  {r.status !== "collected" && r.status !== "cancelled" && (
                    <button
                      onClick={() => advance(r.id, "cancelled")}
                      className="rounded-pill bg-rose-500/15 px-3 py-1 text-xs font-semibold text-rose-600 dark:text-rose-300"
                    >
                      Annuler
                    </button>
                  )}
                </div>
              </div>
              <div className="mt-1 text-xs text-night/50 dark:text-surface/50">
                {r.lines.map((l) => `${l.quantity} × ${l.product_name ?? l.product_id}`).join(", ")}
                {r.pickup_date ? ` · retrait le ${r.pickup_date}` : ""}
                {r.loyalty_credited ? " · points crédités ✓" : ""}
              </div>
            </div>
          ))}
          {reservations.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Aucune réservation. Créez la première ci-dessus.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="text-xs text-night/50 dark:text-surface/50">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
      />
    </div>
  );
}
