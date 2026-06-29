import type { ReactNode } from "react";

const SURFACE =
  "rounded-xl2 border border-night/[0.06] bg-white p-6 shadow-soft " +
  "dark:border-white/10 dark:bg-white/[0.04]";

export function Card({
  title,
  subtitle,
  action,
  children,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={SURFACE}>
      {(title || action) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-bold tracking-tight">{title}</h2>}
            {subtitle && (
              <p className="mt-0.5 text-xs text-night/50 dark:text-surface/50">{subtitle}</p>
            )}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

// KPI : libellé + grande valeur + pastille d'icône optionnelle + indice secondaire.
export function Stat({
  label,
  value,
  icon,
  hint,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div className={SURFACE + " animate-fade-up"}>
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-night/55 dark:text-surface/55">{label}</div>
        {icon && (
          <span className="flex h-9 w-9 items-center justify-center rounded-card bg-brand/10 text-brand">
            {icon}
          </span>
        )}
      </div>
      <div className="mt-2 text-3xl font-extrabold tracking-tight">{value}</div>
      {hint && <div className="mt-1 text-xs text-night/45 dark:text-surface/45">{hint}</div>}
    </div>
  );
}
