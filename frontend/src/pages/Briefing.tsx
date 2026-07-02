import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import {
  completeBriefingItem,
  generateBriefing,
  getBriefing,
  sendBriefing,
  type Briefing as BriefingT,
} from "../api/client";

const CAT: Record<string, { label: string; icon: string; cls: string }> = {
  alert: { label: "Alerte", icon: "⚠️", cls: "bg-rose-500/15 text-rose-600 dark:text-rose-300" },
  markdown: { label: "Démarque", icon: "🏷️", cls: "bg-amber-500/15 text-amber-600 dark:text-amber-300" },
  reassort: { label: "Réassort", icon: "🛒", cls: "bg-brand/15 text-brand-dark dark:text-brand-light" },
  production: { label: "Production", icon: "🥖", cls: "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60" },
  reengagement: { label: "Relance", icon: "📣", cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300" },
};

export default function Briefing() {
  const [briefing, setBriefing] = useState<BriefingT | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    getBriefing().then(setBriefing).catch(() => setBriefing(null));
  }, []);
  useEffect(() => load(), [load]);

  async function generate() {
    setBusy(true);
    try {
      setBriefing(await generateBriefing());
    } finally {
      setBusy(false);
    }
  }
  async function push() {
    if (!briefing) return;
    setBriefing(await sendBriefing(briefing.id));
  }
  async function toggle(id: number, done: boolean) {
    await completeBriefingItem(id, done);
    load();
  }

  const items = briefing?.items ?? [];
  const open = items.filter((i) => !i.done);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Briefing du matin ☀️</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Vos actions du jour, consolidées et priorisées par vos agents IA.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={generate}
            disabled={busy}
            className="rounded-card bg-brand px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Consolidation…" : "Générer le briefing"}
          </button>
          {briefing && (
            <button
              onClick={push}
              className="rounded-card border border-night/15 px-3 py-2 text-sm dark:border-white/15"
            >
              {briefing.status === "sent" ? "Envoyé ✓" : "Envoyer (WhatsApp)"}
            </button>
          )}
        </div>
      </div>

      {!briefing && (
        <Card title="Aucun briefing">
          <div className="flex flex-col items-center py-6 text-center">
            <img
              src="/empty/calm.png"
              alt=""
              width="160"
              height="160"
              className="mb-4 h-40 w-40 opacity-90"
            />
            <p className="max-w-md text-sm text-night/50 dark:text-surface/50">
              Cliquez sur « Générer le briefing » — vos agents (alertes, réassort, démarque,
              production) proposeront les actions du jour.
            </p>
          </div>
        </Card>
      )}

      {briefing && (
        <>
          <Card title={briefing.summary} subtitle={`${briefing.briefing_date ?? ""} · ${open.length} action(s) à traiter`}>
            <div className="space-y-2">
              {items.map((it) => {
                const c = CAT[it.category] ?? CAT.production;
                return (
                  <div
                    key={it.id}
                    className={`flex items-start gap-3 rounded-card border border-night/[0.06] p-3 dark:border-white/10 ${it.done ? "opacity-50" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={it.done}
                      onChange={(e) => toggle(it.id, e.target.checked)}
                      className="mt-1 h-4 w-4 flex-none accent-brand"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-pill px-2 py-0.5 text-[11px] font-semibold ${c.cls}`}>
                          {c.icon} {c.label}
                        </span>
                        <span className={`font-semibold ${it.done ? "line-through" : ""}`}>
                          {it.title}
                        </span>
                        {it.value > 0 && (
                          <span className="text-xs text-brand">~{it.value.toFixed(0)} €</span>
                        )}
                      </div>
                      {it.detail && (
                        <p className="mt-1 text-sm text-night/60 dark:text-surface/60">{it.detail}</p>
                      )}
                      {it.action && (
                        <p className="mt-1 text-xs text-night/40 dark:text-surface/40">
                          → {it.action}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
              {items.length === 0 && (
                <p className="py-4 text-center text-sm text-night/40 dark:text-surface/40">
                  Rien d'urgent aujourd'hui. ☀️
                </p>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
