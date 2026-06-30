import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import ApiAccess from "../components/ApiAccess";
import ConnectorSettings from "../components/ConnectorSettings";
import {
  getConnectors,
  importInvoicesFromEmail,
  syncDwh,
  syncPos,
  pollEquipment,
  type Connector,
} from "../api/client";

const STATUS: Record<string, { label: string; cls: string }> = {
  live: { label: "connecté", cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300" },
  mock: { label: "démo (mock)", cls: "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60" },
  needs_config: { label: "à configurer", cls: "bg-amber-500/15 text-amber-600 dark:text-amber-300" },
};

const CATEGORIES: { key: string; title: string }[] = [
  { key: "messaging", title: "Messagerie" },
  { key: "data", title: "Données" },
  { key: "iot", title: "Capteurs (IoT)" },
  { key: "ai", title: "IA" },
];

export default function Connectors() {
  const [items, setItems] = useState<Connector[]>([]);
  const [explanation, setExplanation] = useState("");
  const [action, setAction] = useState<string | null>(null);

  useEffect(() => {
    getConnectors()
      .then((d) => {
        setItems(d.items);
        setExplanation(d.explanation);
      })
      .catch(() => setExplanation("API injoignable."));
  }, []);

  async function run(label: string, fn: () => Promise<unknown>) {
    setAction(`${label}…`);
    try {
      await fn();
      setAction(`${label} : OK`);
    } catch {
      setAction(`${label} : échec`);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Connecteurs</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">{explanation}</p>
      </div>

      {action && (
        <div className="rounded-card bg-brand/10 px-3 py-2 text-sm text-brand">{action}</div>
      )}

      {CATEGORIES.map((cat) => {
        const list = items.filter((i) => i.category === cat.key);
        if (list.length === 0) return null;
        return (
          <Card key={cat.key} title={cat.title}>
            <div className="grid gap-3 sm:grid-cols-2">
              {list.map((c) => {
                const st = STATUS[c.status] ?? STATUS.mock;
                return (
                  <div
                    key={c.key}
                    className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold">{c.label}</span>
                      <span
                        className={`rounded-pill px-2 py-0.5 text-[11px] font-semibold ${st.cls}`}
                      >
                        {st.label}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-night/50 dark:text-surface/50">
                      mode : <code>{c.provider}</code>
                    </div>
                    {c.status !== "live" && (
                      <div className="mt-2 text-xs text-night/60 dark:text-surface/60">
                        Activer : <code className="break-words">{c.hint}</code>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        );
      })}

      <ConnectorSettings />

      <ApiAccess />

      <Card title="Tester maintenant (mock keyless)" subtitle="Déclenche les connecteurs data existants">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => run("Import email", () => importInvoicesFromEmail())}
            className="rounded-card border border-night/15 px-3 py-1.5 text-sm hover:bg-brand/5 dark:border-white/15"
          >
            Importer factures (email)
          </button>
          <button
            onClick={() => run("Sync caisse", () => syncPos())}
            className="rounded-card border border-night/15 px-3 py-1.5 text-sm hover:bg-brand/5 dark:border-white/15"
          >
            Synchroniser la caisse (POS)
          </button>
          <button
            onClick={() => run("Sync DWH", () => syncDwh())}
            className="rounded-card border border-night/15 px-3 py-1.5 text-sm hover:bg-brand/5 dark:border-white/15"
          >
            Pousser vers l'entrepôt (DWH)
          </button>
          <button
            onClick={() => run("Relevé capteurs", () => pollEquipment())}
            className="rounded-card border border-night/15 px-3 py-1.5 text-sm hover:bg-brand/5 dark:border-white/15"
          >
            Relever les capteurs
          </button>
        </div>
      </Card>
    </div>
  );
}
