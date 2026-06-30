// Composants graphiques légers, sans dépendance (SVG pur) — sobres, premium B2B.
// Choix assumé : pas d'ajout de lib de charting pour garder le build léger et
// l'install reproductible ; ces primitives suffisent aux KPI/sparklines.

export function Sparkline({
  values,
  width = 220,
  height = 48,
  stroke = "#5b8def",
}: {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
}) {
  if (values.length < 2) {
    return <div className="text-xs text-night/40 dark:text-surface/40">données insuffisantes</div>;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * (width - 4) + 2;
    const y = height - 2 - ((v - min) / span) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={stroke}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function MiniBars({
  values,
  width = 220,
  height = 60,
  color = "#5b8def",
}: {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  const max = Math.max(...values, 1);
  const bw = width / Math.max(values.length, 1);
  return (
    <svg width={width} height={height}>
      {values.map((v, i) => {
        const h = (v / max) * (height - 4);
        return (
          <rect
            key={i}
            x={i * bw + 1}
            y={height - h}
            width={Math.max(bw - 2, 1)}
            height={h}
            rx={1.5}
            fill={color}
            opacity={0.85}
          />
        );
      })}
    </svg>
  );
}

// Jauge horizontale 0..1 (risque, confiance) avec couleur selon le niveau.
export function Gauge({ value, danger = false }: { value: number; danger?: boolean }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const color = danger
    ? pct > 66
      ? "bg-rose-500"
      : pct > 33
        ? "bg-amber-500"
        : "bg-emerald-500"
    : "bg-brand";
  return (
    <div className="h-2 w-full overflow-hidden rounded-pill bg-night/10 dark:bg-white/10">
      <div className={`h-full rounded-pill ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

const BADGE: Record<string, string> = {
  critical: "bg-rose-500/15 text-rose-600 dark:text-rose-300",
  high: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  medium: "bg-brand/15 text-brand",
  low: "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60",
  success: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
  running: "bg-brand/15 text-brand",
  failed: "bg-rose-500/15 text-rose-600 dark:text-rose-300",
  open: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  resolved: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
  dismissed: "bg-night/10 text-night/50 dark:bg-white/10 dark:text-surface/50",
  order: "bg-brand/15 text-brand",
  reduce: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  hold: "bg-night/10 text-night/55 dark:bg-white/10 dark:text-surface/55",
};

export function Badge({ value }: { value: string }) {
  const cls = BADGE[value] ?? "bg-night/10 text-night/60 dark:bg-white/10 dark:text-surface/60";
  return (
    <span className={`inline-flex rounded-pill px-2 py-0.5 text-[11px] font-semibold ${cls}`}>
      {value}
    </span>
  );
}
