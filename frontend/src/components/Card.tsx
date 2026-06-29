import type { ReactNode } from "react";

const SURFACE =
  "rounded-card border border-gray-200 bg-white p-5 shadow-soft " +
  "dark:border-white/10 dark:bg-white/5";

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className={SURFACE}>
      {title && <h2 className="mb-3 text-lg font-semibold">{title}</h2>}
      {children}
    </div>
  );
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className={SURFACE}>
      <div className="text-sm text-gray-500 dark:text-gray-400">{label}</div>
      <div className="mt-1 text-2xl font-bold text-brand">{value}</div>
    </div>
  );
}
