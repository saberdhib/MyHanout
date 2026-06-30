import { useCallback, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import { usePolling } from "../hooks/usePolling";
import { useEventStream } from "../hooks/useEventStream";
import { getPipelineHealth, getPipelineRuns, triggerPipeline } from "../api/client";

const JOBS = ["daily", "snapshot_inventory", "ingest_signals", "recommend", "scan_alerts"];

export default function DataOps() {
  const health = usePolling(() => getPipelineHealth(), 15000);
  const runs = usePolling(() => getPipelineRuns(), 12000);
  const [busy, setBusy] = useState<string | null>(null);

  const refreshAll = useCallback(() => {
    health.refresh();
    runs.refresh();
  }, [health, runs]);

  const onEvent = useCallback(
    (e: { type: string }) => {
      if (e.type === "pipeline_finished") refreshAll();
    },
    [refreshAll],
  );
  const { connected } = useEventStream(onEvent);

  async function run(job: string) {
    setBusy(job);
    try {
      await triggerPipeline(job);
      refreshAll();
    } finally {
      setBusy(null);
    }
  }

  function fresh(iso: string | null): string {
    if (!iso) return "—";
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 60) return `il y a ${mins} min`;
    return `il y a ${Math.round(mins / 60)} h`;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Data Ops</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            État des pipelines, fraîcheur des données et déclenchement manuel.{" "}
            <span className={connected ? "text-emerald-600" : "text-night/40"}>
              ● {connected ? "temps réel" : "polling"}
            </span>
          </p>
        </div>
      </div>

      <Card title="Déclencher un job" subtitle="Human-in-the-loop (exécution tracée)">
        <div className="flex flex-wrap gap-2">
          {JOBS.map((job) => (
            <button
              key={job}
              onClick={() => run(job)}
              disabled={busy !== null}
              className="rounded-card border border-night/15 px-3 py-1.5 text-sm font-medium hover:bg-brand/5 disabled:opacity-50 dark:border-white/15"
            >
              {busy === job ? "…" : job}
            </button>
          ))}
        </div>
      </Card>

      <Card title="Santé des jobs" subtitle={health.data?.explanation}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-night/10 text-left text-night/50 dark:border-white/10 dark:text-surface/50">
              <th className="py-2">Job</th>
              <th>Dernier statut</th>
              <th>Fraîcheur</th>
              <th>Erreur</th>
            </tr>
          </thead>
          <tbody>
            {(health.data?.jobs ?? []).map((j) => (
              <tr key={j.job_name} className="border-b border-night/[0.06] last:border-0 dark:border-white/[0.06]">
                <td className="py-2 font-medium">{j.job_name}</td>
                <td>{j.last_status ? <Badge value={j.last_status} /> : "—"}</td>
                <td className="text-night/60 dark:text-surface/60">{fresh(j.data_freshness_at)}</td>
                <td className="max-w-xs truncate text-rose-600">{j.last_error ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Runs récents">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-night/10 text-left text-night/50 dark:border-white/10 dark:text-surface/50">
              <th className="py-2">#</th>
              <th>Job</th>
              <th>Statut</th>
              <th>Déclencheur</th>
              <th>Lignes</th>
              <th>Durée</th>
            </tr>
          </thead>
          <tbody>
            {(runs.data?.items ?? []).map((r) => (
              <tr key={r.id} className="border-b border-night/[0.06] last:border-0 dark:border-white/[0.06]">
                <td className="py-2">{r.id}</td>
                <td className="font-medium">{r.job_name}</td>
                <td><Badge value={r.status} /></td>
                <td className="text-night/60 dark:text-surface/60">{r.trigger}</td>
                <td>{r.rows_processed}</td>
                <td className="text-night/60 dark:text-surface/60">
                  {r.duration_ms != null ? `${r.duration_ms} ms` : "—"}
                </td>
              </tr>
            ))}
            {(runs.data?.items ?? []).length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-night/40 dark:text-surface/40">
                  Aucun run. Déclenche un job ci-dessus.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
