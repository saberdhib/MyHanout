// Jeu d'icônes léger (stroke, style lucide) pour la navigation — sans dépendance.
import type { SVGProps } from "react";

const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const P = (d: string) => (props: SVGProps<SVGSVGElement>) => (
  <svg {...base} {...props}>
    {d.split("|").map((p, i) => (
      <path key={i} d={p} />
    ))}
  </svg>
);

export const Icons: Record<string, (p: SVGProps<SVGSVGElement>) => JSX.Element> = {
  dashboard: P("M3 13h8V3H3zM13 21h8V3h-8zM3 21h8v-6H3z"),
  chat: P("M21 11.5a8.5 8.5 0 0 1-12.3 7.6L3 21l1.9-5.7A8.5 8.5 0 1 1 21 11.5Z"),
  finance: P("M12 1v22|M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"),
  promo: P("M9 11l3 3L22 4|M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"),
  stocks: P("M21 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v3|M3 8h18v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z|M10 12h4"),
  forecast: P("M3 3v18h18|m7 14 3-4 4 3 5-7"),
  suggest: P("M9 18h6|M10 22h4|M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1h6c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2Z"),
  calendar: P("M8 2v4|M16 2v4|M3 10h18|M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"),
  quality: P("M22 11.08V12a10 10 0 1 1-5.93-9.14|M22 4 12 14.01l-3-3"),
  invoice: P("M14 3v4a1 1 0 0 0 1 1h4|M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z|M9 13h6|M9 17h4"),
  plug: P("M9 2v6|M15 2v6|M7 8h10v3a5 5 0 0 1-10 0z|M12 16v6"),
  supplier: P("M3 9l1-5h16l1 5|M5 9v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9|M9 21v-6h6v6"),
  thermometer: P("M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"),
};
