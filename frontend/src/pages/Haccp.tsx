import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import {
  completeHygieneTask,
  createHygieneTask,
  deleteHygieneTask,
  getHaccpRegister,
  getHygieneTasks,
  type HaccpRegister,
  type HygieneTask,
} from "../api/client";

const FREQ: Record<string, string> = { daily: "quotidien", weekly: "hebdo", monthly: "mensuel" };

/** Carnet HACCP : plan de nettoyage tracé + conformité froid + registre de contrôle. */
export default function Haccp() {
  const [tasks, setTasks] = useState<HygieneTask[]>([]);
  const [register, setRegister] = useState<HaccpRegister | null>(null);
  const [name, setName] = useState("");
  const [freq, setFreq] = useState("daily");

  const refresh = useCallback(() => {
    getHygieneTasks().then((d) => setTasks(d.items));
    getHaccpRegister(14).then(setRegister).catch(() => setRegister(null));
  }, []);
  useEffect(refresh, [refresh]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await createHygieneTask(name.trim(), freq);
    setName("");
    refresh();
  }

  const due = tasks.filter((t) => t.due);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Hygiène (HACCP) 🧼</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Plan de nettoyage tracé + relevés de température : votre carnet sanitaire, prêt en
          cas de contrôle. {register?.explanation}
        </p>
      </div>

      <Card
        title={`Tâches du jour (${due.length} à faire)`}
        subtitle="Chaque exécution est horodatée avec son auteur — c'est la preuve HACCP"
      >
        <ul className="space-y-2">
          {tasks.map((t) => (
            <li
              key={t.id}
              className={`flex flex-wrap items-center justify-between gap-2 rounded-card border p-3 ${
                t.due ? "border-amber-400/40 bg-amber-500/5" : "border-night/[0.06] dark:border-white/10"
              }`}
            >
              <div className="min-w-0">
                <div className="font-semibold">
                  {t.name}{" "}
                  <span className="text-xs font-normal text-night/40 dark:text-surface/40">
                    ({FREQ[t.frequency] ?? t.frequency})
                  </span>
                </div>
                <div className="text-xs text-night/50 dark:text-surface/50">
                  {t.last_done_at
                    ? `Dernière fois : ${t.last_done_at.slice(0, 16).replace("T", " ")} par ${t.last_done_by ?? "?"}`
                    : "Jamais exécutée"}
                </div>
              </div>
              <div className="flex gap-2">
                {t.due ? (
                  <button
                    onClick={() => completeHygieneTask(t.id).then(refresh)}
                    className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white"
                  >
                    ✓ Fait
                  </button>
                ) : (
                  <span className="rounded-pill bg-emerald-500/15 px-2 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-300">
                    à jour
                  </span>
                )}
                <button
                  onClick={() => deleteHygieneTask(t.id).then(refresh)}
                  className="text-xs text-rose-600 hover:underline"
                >
                  Retirer
                </button>
              </div>
            </li>
          ))}
        </ul>

        <form onSubmit={add} className="mt-4 flex flex-wrap gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nouvelle tâche (ex. Nettoyage trancheuse)"
            className="min-w-56 flex-1 rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
          <select
            value={freq}
            onChange={(e) => setFreq(e.target.value)}
            className="rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          >
            <option value="daily">quotidien</option>
            <option value="weekly">hebdo</option>
            <option value="monthly">mensuel</option>
          </select>
          <button className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white">
            Ajouter
          </button>
        </form>
      </Card>

      <Card title="Conformité chaîne du froid (14 j)" subtitle="Relevés automatiques des capteurs">
        <div className="grid gap-3 sm:grid-cols-2">
          {(register?.temperature ?? []).map((eq) => (
            <div
              key={eq.equipment_id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">{eq.equipment_name}</span>
                <span
                  className={`text-lg font-bold ${
                    eq.compliance_pct >= 95 ? "text-emerald-600" : "text-rose-600"
                  }`}
                >
                  {eq.compliance_pct.toFixed(0)}%
                </span>
              </div>
              <div className="text-xs text-night/50 dark:text-surface/50">
                plage {eq.min_temp_c}–{eq.max_temp_c}°C · {eq.in_range}/{eq.readings} relevés
                conformes
                {eq.last_temp_c != null && ` · dernier : ${eq.last_temp_c.toFixed(1)}°C`}
              </div>
              {eq.breaches.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-rose-600 dark:text-rose-400">
                  {eq.breaches.map((b, i) => (
                    <li key={i}>⚠️ {b}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          {(register?.temperature ?? []).length === 0 && (
            <p className="py-4 text-sm text-night/40 dark:text-surface/40">
              Aucun équipement suivi — ajoutez vos frigos dans « Équipements ».
            </p>
          )}
        </div>
      </Card>

      <Card
        title="Registre des exécutions"
        subtitle={`${register?.hygiene.length ?? 0} preuve(s) sur ${register?.period_days ?? 14} j — imprimable pour un contrôle`}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-night/50 dark:text-surface/50">
                <th className="py-1">Quand</th>
                <th className="py-1">Tâche</th>
                <th className="py-1">Par</th>
                <th className="py-1">Note</th>
              </tr>
            </thead>
            <tbody>
              {(register?.hygiene ?? []).map((h) => (
                <tr key={h.id} className="border-t border-night/[0.06] dark:border-white/10">
                  <td className="py-1.5">{h.done_at.slice(0, 16).replace("T", " ")}</td>
                  <td className="py-1.5">{h.task_name ?? `#${h.task_id}`}</td>
                  <td className="py-1.5">{h.done_by ?? "—"}</td>
                  <td className="py-1.5">{h.note ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {(register?.hygiene ?? []).length === 0 && (
            <p className="py-4 text-center text-sm text-night/40 dark:text-surface/40">
              Aucune exécution tracée sur la période.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
