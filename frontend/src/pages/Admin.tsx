import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import {
  createRelease,
  getPlatformClients,
  getPlatformOverview,
  getPlatformReleases,
  getPlatformTickets,
  platformReplyTicket,
  platformRole,
  provisionClient,
  publishRelease,
  setClientPlan,
  setClientStatus,
  setTicketStatus,
  type ClientSummary,
  type PlatformOverview,
  type ReleaseNote,
  type Ticket,
} from "../api/client";

const PLANS = ["trial", "starter", "pro", "enterprise"];

// Le badge réutilise la palette existante : on mappe statut commerce -> tonalité connue.
const STATUS_TONE: Record<string, string> = {
  active: "success",
  trial: "medium",
  suspended: "high",
  cancelled: "dismissed",
};

/**
 * Backoffice plateforme (opérateur MyHanout) : pilotage cross-tenant du parc clients.
 * Réservé aux PlatformAdmin — l'API vérifie l'accès en base et audite chaque action.
 */
export default function Admin() {
  const role = platformRole();
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [o, c] = await Promise.all([getPlatformOverview(), getPlatformClients()]);
      setOverview(o);
      setClients(c.items);
      setError(null);
    } catch {
      setError("Accès refusé : réservé aux opérateurs plateforme MyHanout.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!role) {
    return (
      <Card title="Backoffice plateforme">
        <p className="text-sm text-night/60 dark:text-surface/60">
          Espace réservé aux opérateurs MyHanout. Votre compte n'a pas d'accès plateforme.
        </p>
      </Card>
    );
  }

  const toggleStatus = async (c: ClientSummary) => {
    const next = c.status === "suspended" ? "active" : "suspended";
    if (next === "suspended" && !confirm(`Suspendre « ${c.name} » ? Ses utilisateurs perdront l'accès.`))
      return;
    setBusy(true);
    try {
      await setClientStatus(c.organization_id, next);
      await load();
    } finally {
      setBusy(false);
    }
  };

  const changePlan = async (c: ClientSummary, plan: string) => {
    setBusy(true);
    try {
      await setClientPlan(c.organization_id, plan);
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Backoffice plateforme 🛰️</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Pilotage de tous les commerces MyHanout — rôle&nbsp;: <strong>{role}</strong>. Chaque
          action est auditée.
        </p>
      </div>

      {error && (
        <div className="rounded-card border border-rose-500/30 bg-rose-500/5 p-4 text-sm text-rose-600 dark:text-rose-300">
          {error}
        </div>
      )}

      {/* Indicateurs de parc */}
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Kpi label="Clients" value={`${overview?.clients_total ?? "…"}`} />
        <Kpi label="Actifs" value={`${overview?.clients_active ?? "…"}`} />
        <Kpi label="Essai" value={`${overview?.clients_trial ?? "…"}`} />
        <Kpi label="Suspendus" value={`${overview?.clients_suspended ?? "…"}`} />
        <Kpi label="MRR" value={`${(overview?.mrr_total_eur ?? 0).toFixed(0)} €`} />
        <Kpi label="ARR" value={`${(overview?.arr_total_eur ?? 0).toFixed(0)} €`} />
      </div>

      <ProvisionForm
        onDone={async () => {
          await load();
        }}
      />

      <Card title="Parc clients" subtitle={`${clients.length} commerce(s)`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-night/40 dark:text-surface/40">
                <th className="pb-2 pr-3">Commerce</th>
                <th className="pb-2 pr-3">Statut</th>
                <th className="pb-2 pr-3">Plan</th>
                <th className="pb-2 pr-3 text-right">MRR</th>
                <th className="pb-2 pr-3 text-right">Users</th>
                <th className="pb-2 pr-3 text-right">Produits</th>
                <th className="pb-2 pr-3 text-right">Ventes</th>
                <th className="pb-2 pr-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr
                  key={c.organization_id}
                  className="border-t border-night/[0.06] dark:border-white/10"
                >
                  <td className="py-2 pr-3">
                    <div className="font-semibold">{c.name}</div>
                    <div className="text-xs text-night/40 dark:text-surface/40">
                      {c.slug}
                      {c.business_type ? ` · ${c.business_type}` : ""}
                    </div>
                  </td>
                  <td className="py-2 pr-3">
                    <Badge value={STATUS_TONE[c.status] ?? "low"} />
                    <span className="ml-1 text-xs text-night/45 dark:text-surface/45">
                      {c.status}
                    </span>
                  </td>
                  <td className="py-2 pr-3">
                    <select
                      value={PLANS.includes(c.plan) ? c.plan : ""}
                      disabled={busy}
                      onChange={(e) => changePlan(c, e.target.value)}
                      className="rounded-card border border-night/10 bg-transparent px-2 py-1 text-xs dark:border-white/15"
                    >
                      {!PLANS.includes(c.plan) && <option value="">{c.plan}</option>}
                      {PLANS.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{c.mrr_eur.toFixed(0)} €</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{c.users}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{c.products}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{c.sales}</td>
                  <td className="py-2 pr-3">
                    <button
                      disabled={busy}
                      onClick={() => toggleStatus(c)}
                      className={`rounded-pill px-3 py-1 text-xs font-semibold ${
                        c.status === "suspended"
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
                          : "bg-rose-500/15 text-rose-600 dark:text-rose-300"
                      }`}
                    >
                      {c.status === "suspended" ? "Réactiver" : "Suspendre"}
                    </button>
                  </td>
                </tr>
              ))}
              {clients.length === 0 && !error && (
                <tr>
                  <td
                    colSpan={8}
                    className="py-6 text-center text-sm text-night/40 dark:text-surface/40"
                  >
                    Aucun commerce. Provisionnez votre premier client ci-dessus.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {!error && (
        <div className="grid gap-6 lg:grid-cols-2">
          <PlatformTickets />
          <PlatformReleases />
        </div>
      )}
    </div>
  );
}

const TICKET_TONE: Record<string, string> = {
  open: "high",
  pending: "medium",
  resolved: "success",
  closed: "dismissed",
};

function PlatformTickets() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [active, setActive] = useState<Ticket | null>(null);
  const [reply, setReply] = useState("");

  const load = useCallback(async () => {
    setTickets((await getPlatformTickets()).items);
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  const send = async () => {
    if (!active || !reply.trim()) return;
    const t = await platformReplyTicket(active.id, reply.trim());
    setReply("");
    setActive(t);
    await load();
  };
  const resolve = async () => {
    if (!active) return;
    const t = await setTicketStatus(active.id, "resolved");
    setActive(t);
    await load();
  };

  return (
    <Card title="Tickets support" subtitle={`${tickets.length} ticket(s), tous commerces`}>
      <div className="space-y-2">
        {tickets.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t)}
            className={`flex w-full items-center justify-between gap-2 rounded-card border p-3 text-left ${
              active?.id === t.id
                ? "border-brand/40 bg-brand/5"
                : "border-night/[0.06] dark:border-white/10"
            }`}
          >
            <span className="min-w-0 flex-1 truncate text-sm">
              <span className="font-medium">{t.subject}</span>
              <span className="ml-2 text-xs text-night/40 dark:text-surface/40">
                {t.organization_name}
              </span>
            </span>
            <Badge value={TICKET_TONE[t.status] ?? "low"} />
          </button>
        ))}
        {tickets.length === 0 && (
          <p className="py-4 text-center text-sm text-night/40 dark:text-surface/40">
            Aucun ticket ouvert.
          </p>
        )}
      </div>

      {active && (
        <div className="mt-4 space-y-3 border-t border-night/[0.06] pt-4 dark:border-white/10">
          <div className="max-h-56 space-y-2 overflow-y-auto">
            {active.messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-card p-2.5 text-sm ${
                  m.author_kind === "platform" ? "bg-brand/10" : "bg-night/[0.04] dark:bg-white/[0.05]"
                }`}
              >
                <div className="text-[11px] font-semibold uppercase text-night/40 dark:text-surface/40">
                  {m.author_kind === "platform" ? "MyHanout" : "Commerçant"}
                </div>
                {m.body}
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Répondre…"
              className="flex-1 rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
            />
            <button onClick={send} className="rounded-pill bg-brand px-3 py-2 text-xs font-semibold text-white">
              Répondre
            </button>
            <button
              onClick={resolve}
              className="rounded-pill bg-emerald-500/15 px-3 py-2 text-xs font-semibold text-emerald-600 dark:text-emerald-300"
            >
              Résoudre
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}

function PlatformReleases() {
  const [releases, setReleases] = useState<ReleaseNote[]>([]);
  const [form, setForm] = useState({ version: "", title: "", body: "" });

  const load = useCallback(async () => {
    setReleases((await getPlatformReleases()).items);
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  const create = async () => {
    if (!form.version || !form.title || !form.body) return;
    await createRelease(form.version, form.title, form.body);
    setForm({ version: "", title: "", body: "" });
    await load();
  };
  const publish = async (id: number) => {
    await publishRelease(id);
    await load();
  };

  return (
    <Card title="Notes de version" subtitle="Changelog produit publié aux commerces">
      <div className="space-y-2">
        <div className="grid grid-cols-3 gap-2">
          <input
            placeholder="Version"
            value={form.version}
            onChange={(e) => setForm((f) => ({ ...f, version: e.target.value }))}
            className="rounded-card border border-night/10 bg-transparent px-2 py-1.5 text-sm dark:border-white/15"
          />
          <input
            placeholder="Titre"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            className="col-span-2 rounded-card border border-night/10 bg-transparent px-2 py-1.5 text-sm dark:border-white/15"
          />
        </div>
        <textarea
          placeholder="Description"
          rows={2}
          value={form.body}
          onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
          className="w-full rounded-card border border-night/10 bg-transparent px-2 py-1.5 text-sm dark:border-white/15"
        />
        <button
          disabled={!form.version || !form.title || !form.body}
          onClick={create}
          className="rounded-pill bg-brand px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
        >
          Créer (brouillon)
        </button>
      </div>

      <div className="mt-4 space-y-2 border-t border-night/[0.06] pt-4 dark:border-white/10">
        {releases.map((r) => (
          <div key={r.id} className="flex items-center justify-between gap-2 text-sm">
            <span className="min-w-0 flex-1 truncate">
              <span className="font-semibold">v{r.version}</span> · {r.title}
            </span>
            {r.published ? (
              <Badge value="success" />
            ) : (
              <button
                onClick={() => publish(r.id)}
                className="rounded-pill bg-brand/10 px-3 py-1 text-xs font-semibold text-brand-dark dark:text-brand-light"
              >
                Publier
              </button>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function ProvisionForm({ onDone }: { onDone: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    slug: "",
    business_type: "epicerie",
    owner_email: "",
    owner_password: "",
    plan: "trial",
  });
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await provisionClient(form);
      setMsg(`✅ Commerce « ${form.name} » créé.`);
      setForm({
        name: "",
        slug: "",
        business_type: "epicerie",
        owner_email: "",
        owner_password: "",
        plan: "trial",
      });
      await onDone();
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Échec de la création.";
      setMsg(`⚠️ ${detail}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card
      title="Provisionner un commerce"
      subtitle="Crée l'organisation, son compte propriétaire et son abonnement."
      action={
        <button
          onClick={() => setOpen((o) => !o)}
          className="rounded-pill bg-brand/10 px-3 py-1.5 text-xs font-semibold text-brand-dark dark:text-brand-light"
        >
          {open ? "Fermer" : "Nouveau client"}
        </button>
      }
    >
      {open && (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Nom du commerce" value={form.name} onChange={(v) => set("name", v)} />
            <Field
              label="Slug (a-z, 0-9, -)"
              value={form.slug}
              onChange={(v) => set("slug", v.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
            />
            <Field
              label="Type d'activité"
              value={form.business_type}
              onChange={(v) => set("business_type", v)}
            />
            <div>
              <label className="text-xs text-night/50 dark:text-surface/50">Plan</label>
              <select
                value={form.plan}
                onChange={(e) => set("plan", e.target.value)}
                className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
              >
                {PLANS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <Field
              label="Email du propriétaire"
              value={form.owner_email}
              onChange={(v) => set("owner_email", v)}
            />
            <Field
              label="Mot de passe initial"
              type="password"
              value={form.owner_password}
              onChange={(v) => set("owner_password", v)}
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              disabled={busy || !form.name || !form.slug || !form.owner_email || !form.owner_password}
              onClick={submit}
              className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              {busy ? "Création…" : "Créer le commerce"}
            </button>
            {msg && <span className="text-sm text-night/60 dark:text-surface/60">{msg}</span>}
          </div>
        </div>
      )}
    </Card>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="text-xs text-night/50 dark:text-surface/50">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
      />
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-night/[0.06] p-4 dark:border-white/10">
      <div className="text-xs text-night/50 dark:text-surface/50">{label}</div>
      <div className="text-2xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
