import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import {
  createTicket,
  getMyTicket,
  getMyTickets,
  getReleases,
  replyTicket,
  type ReleaseNote,
  type Ticket,
} from "../api/client";

const STATUS_TONE: Record<string, string> = {
  open: "high",
  pending: "medium",
  resolved: "success",
  closed: "dismissed",
};

/** Aide & support : le commerçant ouvre des tickets et suit les nouveautés produit. */
export default function Support() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [active, setActive] = useState<Ticket | null>(null);
  const [releases, setReleases] = useState<ReleaseNote[]>([]);
  const [reply, setReply] = useState("");
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ subject: "", body: "" });

  const load = useCallback(async () => {
    const [t, r] = await Promise.all([getMyTickets(), getReleases()]);
    setTickets(t.items);
    setReleases(r.items);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openTicket = async (id: number) => setActive(await getMyTicket(id));

  const submitNew = async () => {
    if (!form.subject || !form.body) return;
    const t = await createTicket(form.subject, form.body);
    setForm({ subject: "", body: "" });
    setCreating(false);
    await load();
    setActive(t);
  };

  const sendReply = async () => {
    if (!active || !reply.trim()) return;
    const t = await replyTicket(active.id, reply.trim());
    setReply("");
    setActive(t);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Aide & support 💬</h1>
          <p className="text-sm text-night/50 dark:text-surface/50">
            Une question, un souci ? Ouvrez un ticket, l'équipe MyHanout vous répond.
          </p>
        </div>
        <button
          onClick={() => {
            setCreating((c) => !c);
            setActive(null);
          }}
          className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white"
        >
          {creating ? "Fermer" : "Nouveau ticket"}
        </button>
      </div>

      {creating && (
        <Card title="Nouveau ticket">
          <div className="space-y-3">
            <input
              placeholder="Sujet"
              value={form.subject}
              onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
              className="w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
            />
            <textarea
              placeholder="Décrivez votre demande…"
              value={form.body}
              rows={4}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
              className="w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
            />
            <button
              disabled={!form.subject || !form.body}
              onClick={submitNew}
              className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              Envoyer
            </button>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Mes tickets" subtitle={`${tickets.length} ticket(s)`}>
          <div className="space-y-2">
            {tickets.map((t) => (
              <button
                key={t.id}
                onClick={() => openTicket(t.id)}
                className={`flex w-full items-center justify-between gap-2 rounded-card border p-3 text-left transition-colors ${
                  active?.id === t.id
                    ? "border-brand/40 bg-brand/5"
                    : "border-night/[0.06] hover:bg-night/[0.02] dark:border-white/10 dark:hover:bg-white/[0.03]"
                }`}
              >
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{t.subject}</span>
                <Badge value={STATUS_TONE[t.status] ?? "low"} />
              </button>
            ))}
            {tickets.length === 0 && (
              <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
                Aucun ticket. Tout va bien ! 🎉
              </p>
            )}
          </div>
        </Card>

        <Card title={active ? active.subject : "Conversation"}>
          {!active && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Sélectionnez un ticket pour voir la conversation.
            </p>
          )}
          {active && (
            <div className="space-y-3">
              <div className="max-h-80 space-y-3 overflow-y-auto">
                {active.messages.map((m) => (
                  <div
                    key={m.id}
                    className={`rounded-card p-3 text-sm ${
                      m.author_kind === "platform"
                        ? "bg-brand/10"
                        : "bg-night/[0.04] dark:bg-white/[0.05]"
                    }`}
                  >
                    <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-night/40 dark:text-surface/40">
                      {m.author_kind === "platform" ? "Support MyHanout" : "Vous"}
                    </div>
                    {m.body}
                  </div>
                ))}
              </div>
              {active.status !== "closed" && (
                <div className="flex gap-2">
                  <input
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendReply()}
                    placeholder="Votre réponse…"
                    className="flex-1 rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
                  />
                  <button
                    onClick={sendReply}
                    className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white"
                  >
                    Envoyer
                  </button>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card title="Nouveautés produit" subtitle="Les dernières mises à jour de MyHanout">
        <div className="space-y-3">
          {releases.map((r) => (
            <div
              key={r.id}
              className="rounded-card border border-night/[0.06] p-4 dark:border-white/10"
            >
              <div className="flex items-center gap-2">
                <span className="rounded-pill bg-brand/10 px-2 py-0.5 text-[11px] font-semibold text-brand-dark dark:text-brand-light">
                  v{r.version}
                </span>
                <span className="font-semibold">{r.title}</span>
              </div>
              <p className="mt-1 text-sm text-night/70 dark:text-surface/70">{r.body}</p>
            </div>
          ))}
          {releases.length === 0 && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Rien de neuf pour l'instant.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
