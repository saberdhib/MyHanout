import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import {
  getReengagementSegments,
  sendReengagement,
  type ReengagementSegment,
} from "../api/client";

const LABELS: Record<string, string> = {
  reward_ready: "Récompense prête 🎁",
  almost_reward: "Presque une récompense ✨",
  inactive: "À reconquérir 🙂",
};

/** Relance client ciblée : segments (fidélité + activité) → envoi opt-in (RGPD, HITL). */
export default function Reengagement() {
  const [segments, setSegments] = useState<ReengagementSegment[]>([]);
  const [disclaimer, setDisclaimer] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await getReengagementSegments();
    setSegments(r.segments);
    setDisclaimer(r.disclaimer);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const send = async (segment: string, contactable: number) => {
    if (!confirm(`Envoyer la relance à ${contactable} client(s) opt-in ?`)) return;
    setBusy(segment);
    setMsg(null);
    try {
      const r = await sendReengagement(segment);
      setMsg(
        `✅ ${r.sent} envoi(s) · ${r.skipped_no_consent} sans consentement · ` +
          `${r.skipped_no_phone} sans téléphone.`,
      );
      await load();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Relance client 📣</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Des segments prêts à l'emploi, basés sur la fidélité et l'activité. Vous validez, on
          envoie — uniquement aux clients consentants.
        </p>
      </div>

      {msg && (
        <div className="rounded-card border border-brand/30 bg-brand/5 p-3 text-sm">{msg}</div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {segments.map((s) => (
          <Card key={s.segment} title={LABELS[s.segment] ?? s.segment}>
            <div className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums">{s.contactable}</span>
                <span className="text-xs text-night/50 dark:text-surface/50">
                  contactable(s) / {s.total} au total
                </span>
              </div>
              <p className="rounded-card bg-night/[0.03] p-3 text-sm italic dark:bg-white/[0.04]">
                « {s.message} »
              </p>
              <p className="text-xs text-night/50 dark:text-surface/50">{s.explanation}</p>
              <button
                disabled={busy !== null || s.contactable === 0}
                onClick={() => send(s.segment, s.contactable)}
                className="w-full rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                {busy === s.segment ? "Envoi…" : `Relancer (${s.contactable})`}
              </button>
            </div>
          </Card>
        ))}
        {segments.length === 0 && (
          <Card title="Aucun segment à relancer">
            <p className="text-sm text-night/50 dark:text-surface/50">
              Tous vos clients fidèles sont engagés — rien à relancer pour l'instant. 👍
            </p>
          </Card>
        )}
      </div>

      {disclaimer && (
        <p className="text-xs text-night/40 dark:text-surface/40">🔒 {disclaimer}</p>
      )}
    </div>
  );
}
