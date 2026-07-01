import { Card } from "../components/Card";
import { usePolling } from "../hooks/usePolling";
import { getStaffingPlan } from "../api/client";

export default function Staffing() {
  const { data } = usePolling(() => getStaffingPlan(7), 60000);
  const days = data?.days ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Effectifs 🧑‍🍳</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Personnel conseillé selon l'affluence prévue. {data?.explanation}
        </p>
      </div>

      <Card
        title="7 prochains jours"
        subtitle={`Base ${data?.base_staff ?? 1} personne(s) · capacité ~${(data?.units_per_staff ?? 0).toFixed(0)} ventes/personne/jour`}
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {days.map((d) => (
            <div
              key={d.date}
              className={`rounded-card border p-4 ${
                d.delta > 0
                  ? "border-brand/30 bg-brand/5"
                  : "border-night/[0.06] dark:border-white/10"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold capitalize">{d.weekday}</span>
                <span className="text-xs text-night/40 dark:text-surface/40">{d.date.slice(5)}</span>
              </div>
              <div className="mt-2 text-3xl font-bold">
                {d.suggested_staff}
                <span className="ml-1 text-sm font-normal text-night/50 dark:text-surface/50">
                  pers.
                </span>
              </div>
              <div className="mt-1 text-xs">
                {d.delta > 0 ? (
                  <span className="font-semibold text-brand">+{d.delta} renfort</span>
                ) : (
                  <span className="text-night/40 dark:text-surface/40">effectif de base</span>
                )}
                <span className="ml-2 text-night/40 dark:text-surface/40">
                  ({d.vs_average_pct > 0 ? "+" : ""}
                  {d.vs_average_pct.toFixed(0)}% vs moy.)
                </span>
              </div>
            </div>
          ))}
          {days.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Pas encore assez de ventes pour estimer l'affluence.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
