import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import {
  generatePromoVisual,
  getPromos,
  publishPromo,
  scanPromos,
  type Promo,
} from "../api/client";

// Aperçu façon bulle WhatsApp du message promo (preview avant publication).
function WhatsAppBubble({ text }: { text: string }) {
  return (
    <div className="rounded-card bg-[#0b141a] p-3">
      <div className="ml-auto max-w-[90%] rounded-lg rounded-tr-none bg-[#005c4b] px-3 py-2 text-sm text-white whitespace-pre-line">
        {text}
        <span className="ml-2 align-bottom text-[10px] text-white/60">✓✓</span>
      </div>
    </div>
  );
}

// Promos flash : produits en fin de vie -> proposition IA -> affiche + publication validée.
export default function Promos() {
  const [promos, setPromos] = useState<Promo[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

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

  async function makeVisual(id: number) {
    setBusy(id);
    try {
      await generatePromoVisual(id);
      setMsg(`Affiche générée pour la promo #${id}.`);
      await refresh();
    } finally {
      setBusy(null);
    }
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
            <WhatsAppBubble text={p.message} />
            {p.reason && <p className="mt-2 text-xs text-gray-500">Pourquoi : {p.reason}</p>}

            {p.visual_url && (
              <img
                src={p.visual_url}
                alt={`Affiche promo ${p.title}`}
                className="mt-3 w-full rounded-card border border-black/5"
              />
            )}

            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
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
              <div className="flex gap-2">
                <button
                  onClick={() => makeVisual(p.id)}
                  disabled={busy === p.id}
                  className="rounded-card border border-brand px-3 py-1 text-xs text-brand disabled:opacity-50"
                >
                  {busy === p.id ? "Génération…" : p.visual_url ? "🎨 Régénérer l'affiche" : "🎨 Générer une affiche"}
                </button>
                {p.status === "draft" && (
                  <button
                    onClick={() => publish(p.id)}
                    className="rounded-card bg-brand px-3 py-1 text-xs text-white"
                  >
                    Publier (réseaux + clients opt-in)
                  </button>
                )}
              </div>
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
