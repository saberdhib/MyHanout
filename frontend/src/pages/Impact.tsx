import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { getImpact, type ImpactView } from "../api/client";

const KIND_TONE: Record<string, string> = {
  gain: "text-emerald-600 dark:text-emerald-400",
  detected: "text-amber-600 dark:text-amber-400",
  revenue: "text-brand-dark dark:text-brand-light",
  time: "text-night/70 dark:text-surface/70",
};

/** Tableau d'impact : combien l'outil a fait gagner / révélé, en euros. */
export default function Impact() {
  const [data, setData] = useState<ImpactView | null>(null);
  const [days, setDays] = useState(30);

  const load = useCallback(async () => setData(await getImpact(days)), [days]);
  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Impact 📈</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Ce que MyHanout vous a fait gagner ou révélé. {data?.disclaimer}
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
        >
          <option value={7}>7 jours</option>
          <option value={30}>30 jours</option>
          <option value={90}>90 jours</option>
        </select>
      </div>

      {/* Chiffre héros */}
      <div className="rounded-xl2 border border-emerald-500/20 bg-emerald-500/[0.06] p-6 text-center">
        <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700/70 dark:text-emerald-300/70">
          Valeur gagnée ou révélée sur {data?.period_days ?? days} jours
        </div>
        <div className="mt-1 text-4xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">
          {(data?.estimated_value_eur ?? 0).toFixed(0)} €
        </div>
        <div className="mt-1 text-sm text-night/50 dark:text-surface/50">
          + ~{data?.time_saved_hours ?? 0} h de temps gagné · {(data?.revenue ?? 0).toFixed(0)} € de
          CA sur la période
        </div>
      </div>

      <Card title="Détail" subtitle={data?.explanation}>
        <div className="space-y-2">
          {(data?.lines ?? []).map((ln) => (
            <div
              key={ln.label}
              className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-night/[0.06] p-3 dark:border-white/10"
            >
              <div className="min-w-0">
                <div className="text-sm font-semibold">{ln.label}</div>
                <div className="text-xs text-night/50 dark:text-surface/50">{ln.explanation}</div>
              </div>
              <div className={`text-lg font-bold tabular-nums ${KIND_TONE[ln.kind] ?? ""}`}>
                {ln.unit === "€" ? `${ln.amount.toFixed(0)} €` : `${ln.amount} ${ln.unit}`}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
