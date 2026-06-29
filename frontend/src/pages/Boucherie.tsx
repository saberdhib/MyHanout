import { useEffect, useState } from "react";
import { Card, Stat } from "../components/Card";
import {
  createMeatLot,
  getMeatLot,
  getMeatLots,
  setMeatBreakdown,
  type MeatCutIn,
  type MeatLotRow,
  type MeatLotSummary,
} from "../api/client";

const eur = (n: number) => `${n.toFixed(2)} €`;

// Boucherie : on achète une bête au poids → on décompose → rendement + coût/kg + traçabilité.
export default function Boucherie() {
  const [lots, setLots] = useState<MeatLotRow[]>([]);
  const [selected, setSelected] = useState<MeatLotSummary | null>(null);
  const [cuts, setCuts] = useState<MeatCutIn[]>([]);

  const refresh = () => getMeatLots().then(setLots).catch(() => setLots([]));
  useEffect(() => {
    refresh();
  }, []);

  async function open(id: number) {
    const s = await getMeatLot(id);
    setSelected(s);
    setCuts(
      s.cuts.length
        ? s.cuts.map((c) => ({
            cut_label: c.cut_label,
            actual_weight_kg: c.actual_weight_kg ?? undefined,
            is_waste: c.is_waste,
          }))
        : [
            { cut_label: "", actual_weight_kg: undefined, is_waste: false },
            { cut_label: "os / perte", actual_weight_kg: undefined, is_waste: true },
          ],
    );
  }

  async function addLot() {
    const code = `BOV-${Date.now().toString().slice(-6)}`;
    const s = await createMeatLot({
      lot_code: code,
      species: "boeuf",
      label: "demi-bœuf",
      gross_weight_kg: 150,
      purchase_cost: 1200,
    });
    await refresh();
    open(s.id);
  }

  async function saveBreakdown() {
    if (!selected) return;
    const clean = cuts.filter((c) => c.cut_label.trim());
    const s = await setMeatBreakdown(selected.id, clean);
    setSelected(s);
    refresh();
  }

  function updateCut(i: number, patch: Partial<MeatCutIn>) {
    setCuts((cs) => cs.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">Boucherie — lots & traçabilité</h1>
          <p className="page-sub">
            Achat d'une bête au poids → découpe/désossage → rendement, coût au kilo et traçabilité.
          </p>
        </div>
        <button onClick={addLot} className="btn-primary">
          + Réceptionner une bête
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Liste des lots */}
        <Card title="Lots reçus">
          <ul className="space-y-2">
            {lots.map((l) => (
              <li key={l.id}>
                <button
                  onClick={() => open(l.id)}
                  className={`w-full rounded-card border p-3 text-left text-sm transition-colors ${
                    selected?.id === l.id
                      ? "border-brand bg-brand/5"
                      : "border-night/[0.06] hover:bg-surface dark:border-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{l.label}</span>
                    <span className="pill bg-night/5 dark:bg-white/10">{l.status}</span>
                  </div>
                  <div className="mt-1 text-xs text-night/50 dark:text-surface/50">
                    {l.lot_code} · {l.gross_weight_kg} kg · {eur(l.purchase_cost)}
                  </div>
                </button>
              </li>
            ))}
            {lots.length === 0 && (
              <p className="text-sm text-night/40 dark:text-surface/40">
                Aucun lot. Réceptionnez une bête.
              </p>
            )}
          </ul>
        </Card>

        {/* Détail / décomposition */}
        {selected ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Poids brut" value={`${selected.gross_weight_kg} kg`} icon="🐄" />
              <Stat
                label="Rendement"
                value={selected.yield_pct != null ? `${(selected.yield_pct * 100).toFixed(0)}%` : "—"}
                icon="⚖️"
              />
              <Stat
                label="Coût / kg"
                value={selected.cost_per_kg != null ? eur(selected.cost_per_kg) : "—"}
                icon="💶"
                hint="valorisable"
              />
              <Stat label="Perte (os)" value={`${selected.waste_weight_kg} kg`} icon="🦴" />
            </div>

            <Card title="Décomposition" subtitle={selected.traceability}>
              <div className="space-y-2">
                {cuts.map((c, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2">
                    <input
                      value={c.cut_label}
                      onChange={(e) => updateCut(i, { cut_label: e.target.value })}
                      placeholder="pièce (aloyau, épaule…)"
                      className="min-w-[160px] flex-1 rounded-card border border-night/10 px-3 py-1.5 text-sm dark:border-white/15 dark:bg-night dark:text-surface"
                    />
                    <input
                      type="number"
                      value={c.actual_weight_kg ?? ""}
                      onChange={(e) =>
                        updateCut(i, {
                          actual_weight_kg: e.target.value ? Number(e.target.value) : undefined,
                        })
                      }
                      placeholder="kg réel"
                      className="w-24 rounded-card border border-night/10 px-3 py-1.5 text-sm dark:border-white/15 dark:bg-night dark:text-surface"
                    />
                    <label className="flex items-center gap-1 text-xs text-night/60 dark:text-surface/60">
                      <input
                        type="checkbox"
                        checked={c.is_waste ?? false}
                        onChange={(e) => updateCut(i, { is_waste: e.target.checked })}
                      />
                      os/perte
                    </label>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => setCuts((cs) => [...cs, { cut_label: "", is_waste: false }])}
                  className="btn-ghost text-xs"
                >
                  + pièce
                </button>
                <button onClick={saveBreakdown} className="btn-primary text-xs">
                  Enregistrer & calculer
                </button>
              </div>

              {selected.cuts.length > 0 && (
                <table className="mt-4 w-full text-sm">
                  <thead>
                    <tr className="border-b border-night/[0.06] text-left text-night/50 dark:border-white/10 dark:text-surface/50">
                      <th className="py-1">Pièce</th>
                      <th className="text-right">kg</th>
                      <th className="text-right">Coût alloué</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.cuts.map((c) => (
                      <tr key={c.id} className="border-b border-night/[0.04] last:border-0">
                        <td className="py-1" title={c.explanation ?? ""}>
                          {c.cut_label} {c.is_waste && <span className="text-night/40">(perte)</span>}
                        </td>
                        <td className="text-right tabular-nums">{c.actual_weight_kg ?? "—"}</td>
                        <td className="text-right tabular-nums">
                          {c.allocated_cost != null ? eur(c.allocated_cost) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <p className="mt-3 text-xs text-night/50 dark:text-surface/50">{selected.explanation}</p>
            </Card>
          </div>
        ) : (
          <Card>
            <p className="text-sm text-night/40 dark:text-surface/40">
              Sélectionnez un lot (ou réceptionnez une bête) pour saisir la décomposition.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
