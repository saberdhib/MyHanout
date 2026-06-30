import { useCallback, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { useEventStream } from "../hooks/useEventStream";
import { getAlerts, resolveAlert } from "../api/client";

export default function Alerts() {
  const [filter, setFilter] = useState<string>("open");
  const { data, refresh } = usePolling(
    () => getAlerts(filter === "all" ? undefined : filter),
    12000,
  );

  // Temps réel : une nouvelle alerte (ou résolution) rafraîchit la liste.
  const onEvent = useCallback(
    (e: { type: string }) => {
      if (e.type === "alert_created" || e.type === "alert_resolved") refresh();
    },
    [refresh],
  );
  const { connected } = useEventStream(onEvent);

  async function act(id: number, dismiss: boolean) {
    await resolveAlert(id, dismiss ? "faux positif" : "traité", dismiss);
    refresh();
  }

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Alertes</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Règles lisibles → priorité → résolution humaine.{" "}
            <span className={connected ? "text-emerald-600" : "text-night/40"}>
              ● {connected ? "temps réel" : "polling"}
            </span>
          </p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
        >
          <option value="open">Ouvertes</option>
          <option value="resolved">Résolues</option>
          <option value="dismissed">Écartées</option>
          <option value="all">Toutes</option>
        </select>
      </div>

      <Card title={`${items.length} alerte(s)`}>
        <div className="space-y-3">
          {items.map((a) => (
            <div
              key={a.id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">
                  {a.title} <Badge value={a.priority} /> <Badge value={a.status} />
                </div>
                <Badge value={a.kind} />
              </div>
              {a.message && (
                <p className="mt-1 text-sm text-night/70 dark:text-surface/70">{a.message}</p>
              )}
              <div className="mt-1 text-xs text-night/50 dark:text-surface/50">
                {a.rule && <span>Règle : <code>{a.rule}</code>. </span>}
                {a.recommended_action && <span>Action : {a.recommended_action}</span>}
              </div>
              {a.status === "open" && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => act(a.id, false)}
                    className="rounded-card bg-brand px-3 py-1 text-sm font-semibold text-white"
                  >
                    Marquer résolue
                  </button>
                  <button
                    onClick={() => act(a.id, true)}
                    className="rounded-card border border-night/15 px-3 py-1 text-sm dark:border-white/15"
                  >
                    Écarter (faux positif)
                  </button>
                </div>
              )}
            </div>
          ))}
          {items.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Aucune alerte {filter !== "all" ? `(${filter})` : ""}.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
