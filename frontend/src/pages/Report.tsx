import { useState } from "react";
import { Card } from "../components/Card";
import { usePolling } from "../hooks/usePolling";
import { getWeeklyReport, sendWeeklyReport } from "../api/client";

export default function Report() {
  const { data } = usePolling(() => getWeeklyReport(), 60000);
  const [sent, setSent] = useState(false);

  async function push() {
    await sendWeeklyReport();
    setSent(true);
  }

  const r = data;
  const up = (r?.revenue_delta_pct ?? 0) >= 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Bilan hebdo 📊</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            {r ? `Semaine du ${r.period_start} au ${r.period_end}` : "Consolidation de la semaine…"}
          </p>
        </div>
        <button
          onClick={push}
          className="rounded-card border border-night/15 px-3 py-2 text-sm dark:border-white/15"
        >
          {sent ? "Envoyé ✓" : "Envoyer (WhatsApp)"}
        </button>
      </div>

      {r && (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <Kpi
              label="Chiffre d'affaires"
              value={`${r.revenue.toFixed(0)} €`}
              sub={`${up ? "↗" : "↘"} ${r.revenue_delta_pct.toFixed(0)}% vs S-1`}
              accent
            />
            <Kpi label="Marge brute" value={`${r.gross_margin_pct.toFixed(0)}%`} sub={`${r.gross_margin.toFixed(0)} €`} />
            <Kpi label="Unités vendues" value={`${r.units_sold.toFixed(0)}`} />
            <Kpi label="Récupéré (anti-gaspi)" value={`${r.markdown_recovered.toFixed(0)} €`} />
          </div>

          <Card title="Points clés" subtitle={r.narrative}>
            <ul className="space-y-1.5 text-sm">
              {r.highlights.map((h, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-brand">•</span>
                  {h}
                </li>
              ))}
            </ul>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="À faire cette semaine">
              <ul className="space-y-1.5 text-sm">
                {r.actions.map((a, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-brand">→</span>
                    {a}
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="Meilleures ventes">
              <ul className="space-y-1.5 text-sm">
                {r.top_products.map((t) => (
                  <li key={t.product_id} className="flex items-center justify-between">
                    <span>{t.name ?? `#${t.product_id}`}</span>
                    <span className="font-semibold">{t.revenue.toFixed(0)} €</span>
                  </li>
                ))}
                {r.top_products.length === 0 && (
                  <li className="text-night/40 dark:text-surface/40">Pas de vente sur la période.</li>
                )}
              </ul>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className="rounded-card border border-night/[0.06] p-4 dark:border-white/10">
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className={`text-2xl font-bold ${accent ? "text-brand" : ""}`}>{value}</div>
      {sub && <div className="text-xs text-night/40 dark:text-surface/40">{sub}</div>}
    </div>
  );
}
