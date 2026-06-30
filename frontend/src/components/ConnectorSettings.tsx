import { useEffect, useState } from "react";
import { Card } from "./Card";
import {
  deleteConnector,
  getConnectorSettings,
  saveConnector,
  type ConnectorStatus,
} from "../api/client";

/**
 * Modèle B : chaque commerce branche SON WhatsApp/Slack/Telegram.
 * Les secrets ne sont jamais réaffichés (champs vides = inchangés à la maj).
 */
type Field = { key: string; label: string; secret?: boolean; placeholder?: string };

const SPECS: { kind: string; label: string; help: string; fields: Field[] }[] = [
  {
    kind: "whatsapp",
    label: "WhatsApp Business",
    help: "Cloud API Meta — depuis developers.facebook.com (Phone Number ID + token).",
    fields: [
      { key: "phone_number_id", label: "Phone Number ID", placeholder: "123456789012345" },
      { key: "access_token", label: "Access token", secret: true },
      { key: "app_secret", label: "App secret", secret: true },
      { key: "verify_token", label: "Verify token (webhook)", placeholder: "ma-chaine-secrete" },
    ],
  },
  {
    kind: "slack",
    label: "Slack",
    help: "Bot token (xoxb-…) depuis api.slack.com/apps → OAuth & Permissions.",
    fields: [{ key: "bot_token", label: "Bot token", secret: true, placeholder: "xoxb-…" }],
  },
  {
    kind: "telegram",
    label: "Telegram",
    help: "Bot token donné par @BotFather.",
    fields: [{ key: "bot_token", label: "Bot token", secret: true, placeholder: "123456:ABC-…" }],
  },
];

export default function ConnectorSettings() {
  const [status, setStatus] = useState<ConnectorStatus[]>([]);
  const [msg, setMsg] = useState("");

  function refresh() {
    getConnectorSettings()
      .then(setStatus)
      .catch(() => setStatus([]));
  }
  useEffect(refresh, []);

  return (
    <Card
      title="Mes connexions (WhatsApp, Slack, Telegram)"
      subtitle="Branchez vos propres comptes — vos identifiants sont chiffrés et jamais réaffichés."
    >
      {msg && <div className="mb-3 rounded-card bg-brand/10 px-3 py-2 text-sm text-brand">{msg}</div>}
      <div className="space-y-4">
        {SPECS.map((spec) => {
          const st = status.find((s) => s.kind === spec.kind);
          return (
            <ConnectorForm
              key={spec.kind}
              spec={spec}
              status={st}
              onSaved={(m) => {
                setMsg(m);
                refresh();
              }}
            />
          );
        })}
      </div>
    </Card>
  );
}

function ConnectorForm({
  spec,
  status,
  onSaved,
}: {
  spec: { kind: string; label: string; help: string; fields: Field[] };
  status?: ConnectorStatus;
  onSaved: (msg: string) => void;
}) {
  const [vals, setVals] = useState<Record<string, string>>({});

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await saveConnector(spec.kind, vals);
    setVals({});
    onSaved(`« ${spec.label} » enregistré ✓`);
  }
  async function remove() {
    await deleteConnector(spec.kind);
    onSaved(`« ${spec.label} » débranché.`);
  }

  const badge = status?.configured
    ? { t: "connecté", c: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300" }
    : { t: "à configurer", c: "bg-amber-500/15 text-amber-600 dark:text-amber-300" };

  return (
    <form
      onSubmit={save}
      className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold">{spec.label}</span>
        <span className={`rounded-pill px-2 py-0.5 text-[11px] font-semibold ${badge.c}`}>
          {badge.t}
        </span>
      </div>
      <p className="mt-1 text-xs text-night/50 dark:text-surface/50">{spec.help}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {spec.fields.map((f) => (
          <label key={f.key} className="text-xs text-night/60 dark:text-surface/60">
            {f.label}
            {f.secret && status?.has_secret && (
              <span className="ml-1 text-night/30 dark:text-surface/30">(déjà saisi)</span>
            )}
            <input
              type={f.secret ? "password" : "text"}
              value={vals[f.key] ?? (f.secret ? "" : (status?.public?.[f.key] ?? ""))}
              onChange={(e) => setVals({ ...vals, [f.key]: e.target.value })}
              placeholder={f.placeholder ?? (f.secret ? "•••••• (laisser vide = inchangé)" : "")}
              className="mt-0.5 w-full rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
            />
          </label>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white">
          Enregistrer
        </button>
        {status?.configured && (
          <button
            type="button"
            onClick={remove}
            className="rounded-card border border-night/15 px-3 py-1.5 text-sm text-rose-600 dark:border-white/15"
          >
            Débrancher
          </button>
        )}
      </div>
    </form>
  );
}
