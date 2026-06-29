import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { getPromos, publishPromo, scanPromos, type Promo } from "../api/client";

// Promos flash : produits en fin de vie -> proposition IA -> publication validée.
export default function Promos() {
  const [promos, setPromos] = useState<Promo[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = () => getPromos().then((r) => setPromos(r.items)).catch(() => setPromos([]));
  useEffect(() => {
    refresh();
  }, []);

  async function scan() {
    setMsg(null);
    const r = await scanPromos(3);
    setMsg(`${r.total} promo(s) proposée(s) sur produits en fin de vie.`);
    refresh();
  }

  async function publish(id: number) {
    const p = await publishPromo(id);
    setMsg(`Promo #${p.id} publiée → ${p.audience_count} client(s) opt-in + réseaux.`);
    refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Promos flash</h1>
        <button onClick={scan} className="rounded-card bg-brand px-3 py-1 text-sm text-white">
          🔎 Scanner les fins de vie
        </button>
      </div>
      {msg && <div className="rounded-card bg-green-50 p-3 text-sm text-green-800">{msg}</div>}
      <div className="grid gap-4 sm:grid-cols-2">
        {promos.map((p) => (
          <Card key={p.id} title={`${p.title} · -${p.discount_pct}%`}>
            <p className="text-sm">{p.message}</p>
            {p.reason && <p className="mt-2 text-xs text-gray-500">Pourquoi : {p.reason}</p>}
            <div className="mt-3 flex items-center justify-between">
              <span
                className={`rounded-pill px-2 py-0.5 text-xs ${
                  p.status === "published"
                    ? "bg-green-100 text-green-700"
                    : "bg-accent/20 text-accent"
                }`}
              >
                {p.status}
                {p.status === "published" && ` · ${p.audience_count} clients`}
              </span>
              {p.status === "draft" && (
                <button
                  onClick={() => publish(p.id)}
                  className="rounded-card bg-brand px-3 py-1 text-xs text-white"
                >
                  Publier (réseaux + clients opt-in)
                </button>
              )}
            </div>
          </Card>
        ))}
        {promos.length === 0 && (
          <p className="text-sm text-gray-400">Aucune promo. Lancez un scan.</p>
        )}
      </div>
    </div>
  );
}
