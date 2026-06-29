import { useEffect, useState } from "react";
import { Card, Stat } from "../components/Card";
import {
  createEquipment,
  getEquipment,
  pollEquipment,
  type EquipmentStatus,
} from "../api/client";

const KIND_LABEL: Record<string, string> = {
  fridge: "Réfrigérateur",
  freezer: "Congélateur",
  oven: "Four",
  other: "Machine",
};
const KIND_ICON: Record<string, string> = { fridge: "🧊", freezer: "❄️", oven: "🔥", other: "⚙️" };

function statusPill(s: string) {
  if (s === "ok") return "bg-brand/10 text-brand-dark dark:text-brand-light";
  if (s === "alert") return "bg-red-100 text-red-700";
  return "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60";
}

export default function Equipment() {
  const [items, setItems] = useState<EquipmentStatus[]>([]);
  const [alerts, setAlerts] = useState(0);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const refresh = () =>
    getEquipment()
      .then((r) => {
        setItems(r.items);
        setAlerts(r.alerts);
      })
      .catch(() => setItems([]));
  useEffect(() => {
    refresh();
  }, []);

  async function poll() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await pollEquipment();
      setMsg(`Relevé effectué (${r.provider}) — ${r.readings} mesure(s), ${r.alerts} alerte(s).`);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function addExample() {
    setAdding(true);
    try {
      await createEquipment({
        name: "Nouveau frigo",
        kind: "fridge",
        location: "Magasin",
        min_temp_c: 0,
        max_temp_c: 4,
        sensor_external_id: `sensor-${Date.now()}`,
      });
      await refresh();
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Équipements & chaîne du froid</h1>
          <p className="page-sub">
            Suivi des températures (HACCP). Sans thermomètre connecté, des relevés de démo sont
            simulés — branchez vos capteurs quand vous voulez.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={addExample} disabled={adding} className="btn-ghost disabled:opacity-50">
            + Équipement
          </button>
          <button onClick={poll} disabled={busy} className="btn-primary disabled:opacity-50">
            {busy ? "Relevé…" : "🌡️ Relever maintenant"}
          </button>
        </div>
      </div>

      {msg && (
        <div className="rounded-card bg-brand/10 p-3 text-sm text-brand-dark dark:text-brand-light">
          {msg}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Équipements suivis" value={items.length} icon="🌡️" />
        <Stat
          label="En alerte"
          value={alerts}
          icon="🚨"
          hint={alerts ? "chaîne du froid à vérifier" : "tout est dans les plages"}
        />
        <Stat
          label="Capteurs connectés"
          value={items.filter((i) => i.last_temp_c != null).length}
          icon="📡"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((e) => (
          <Card key={e.id}>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl">{KIND_ICON[e.kind] ?? "⚙️"}</span>
                  <h3 className="font-bold">{e.name}</h3>
                </div>
                <p className="mt-0.5 text-xs text-night/50 dark:text-surface/50">
                  {KIND_LABEL[e.kind] ?? e.kind}
                  {e.location ? ` · ${e.location}` : ""}
                </p>
              </div>
              <span className={`pill ${statusPill(e.status)}`}>
                {e.status === "ok" ? "✓ OK" : e.status === "alert" ? "⚠️ Alerte" : "—"}
              </span>
            </div>

            <div className="mt-4 flex items-end gap-2">
              <span
                className={`text-4xl font-extrabold tracking-tight ${e.status === "alert" ? "text-red-500" : ""}`}
              >
                {e.last_temp_c != null ? `${e.last_temp_c.toFixed(1)}°` : "—"}
              </span>
              <span className="mb-1 text-sm text-night/50 dark:text-surface/50">
                plage {e.min_temp_c}…{e.max_temp_c}°C
              </span>
            </div>
            <p className="mt-2 text-xs text-night/60 dark:text-surface/60">{e.explanation}</p>
          </Card>
        ))}
        {items.length === 0 && (
          <p className="text-sm text-night/40 dark:text-surface/40">
            Aucun équipement. Ajoutez-en un puis lancez un relevé.
          </p>
        )}
      </div>
    </div>
  );
}
