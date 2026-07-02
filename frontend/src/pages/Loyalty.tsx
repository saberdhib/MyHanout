import { useCallback, useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Badge } from "../components/Charts";
import {
  earnPoints,
  getCustomers,
  getLoyalty,
  getLoyaltyDetail,
  redeemReward,
  type Customer,
  type LoyaltyAccount,
  type LoyaltyDetail,
} from "../api/client";

/** Fidélité client : cumul de points explicable + échange de récompense (human-in-the-loop). */
export default function Loyalty() {
  const [accounts, setAccounts] = useState<LoyaltyAccount[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [detail, setDetail] = useState<LoyaltyDetail | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [form, setForm] = useState({ customer_id: "", amount: "" });

  const load = useCallback(async () => {
    const [a, c] = await Promise.all([getLoyalty(), getCustomers()]);
    setAccounts(a.items);
    setCustomers(c.items);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const open = async (cid: number) => setDetail(await getLoyaltyDetail(cid));

  const earn = async () => {
    const cid = Number(form.customer_id);
    const amount = Number(form.amount);
    if (!cid || !amount) return;
    const acc = await earnPoints(cid, amount);
    setMsg(`+${acc.points_balance - (accounts.find((a) => a.customer_id === cid)?.points_balance ?? 0)} pts · ${acc.explanation}`);
    setForm({ customer_id: "", amount: "" });
    await load();
    if (detail?.customer_id === cid) await open(cid);
  };

  const redeem = async (cid: number) => {
    if (!confirm("Échanger un palier de points contre la récompense ?")) return;
    const r = await redeemReward(cid);
    setMsg(r.explanation);
    await load();
    await open(cid);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Fidélité client 🎁</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          Récompensez vos habitués : chaque achat cumule des points, échangeables contre une
          récompense. Vous gardez la main sur chaque geste.
        </p>
      </div>

      {msg && (
        <div className="rounded-card border border-brand/30 bg-brand/5 p-3 text-sm">{msg}</div>
      )}

      <Card title="Attribuer des points" subtitle="Sur un achat en caisse (action manuelle)">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-48 flex-1">
            <label className="text-xs text-night/50 dark:text-surface/50">Client</label>
            <select
              value={form.customer_id}
              onChange={(e) => setForm((f) => ({ ...f, customer_id: e.target.value }))}
              className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
            >
              <option value="">— choisir —</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name ?? `Client #${c.id}`}
                  {c.consent_opt_in ? "" : " (sans opt-in)"}
                </option>
              ))}
            </select>
          </div>
          <div className="w-32">
            <label className="text-xs text-night/50 dark:text-surface/50">Montant (€)</label>
            <input
              type="number"
              value={form.amount}
              onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              className="mt-1 w-full rounded-card border border-night/10 bg-transparent px-3 py-2 text-sm dark:border-white/15"
            />
          </div>
          <button
            disabled={!form.customer_id || !form.amount}
            onClick={earn}
            className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            Créditer
          </button>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Comptes fidélité" subtitle={`${accounts.length} client(s)`}>
          <div className="space-y-2">
            {accounts.map((a) => (
              <div
                key={a.customer_id}
                className="flex items-center justify-between gap-2 rounded-card border border-night/[0.06] p-3 dark:border-white/10"
              >
                <button className="min-w-0 flex-1 text-left" onClick={() => open(a.customer_id)}>
                  <div className="truncate text-sm font-semibold">
                    {a.customer_name ?? `Client #${a.customer_id}`}
                  </div>
                  <div className="text-xs text-night/50 dark:text-surface/50">{a.explanation}</div>
                </button>
                <div className="flex items-center gap-2">
                  <span className="font-bold tabular-nums">{a.points_balance} pts</span>
                  {a.reward_ready && (
                    <button
                      onClick={() => redeem(a.customer_id)}
                      className="rounded-pill bg-emerald-500/15 px-3 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-300"
                    >
                      Échanger
                    </button>
                  )}
                </div>
              </div>
            ))}
            {accounts.length === 0 && (
              <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
                Aucun compte fidélité. Créditez un premier achat ci-dessus.
              </p>
            )}
          </div>
        </Card>

        <Card title={detail ? `Historique — ${detail.customer_name ?? ""}` : "Historique"}>
          {!detail && (
            <p className="py-6 text-center text-sm text-night/40 dark:text-surface/40">
              Sélectionnez un client pour voir son grand livre de points.
            </p>
          )}
          {detail && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-sm">
                <span className="font-bold">{detail.points_balance} pts</span>
                <span className="text-night/50 dark:text-surface/50">
                  cumul {detail.lifetime_points} · {detail.explanation}
                </span>
              </div>
              <div className="max-h-72 space-y-1.5 overflow-y-auto">
                {detail.transactions.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between gap-2 rounded-card bg-night/[0.03] px-3 py-2 text-sm dark:bg-white/[0.04]"
                  >
                    <span className="min-w-0 flex-1 truncate">
                      <Badge value={t.kind === "redeem" ? "reduce" : "success"} /> {t.reason}
                    </span>
                    <span
                      className={`font-semibold tabular-nums ${
                        t.points < 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"
                      }`}
                    >
                      {t.points > 0 ? "+" : ""}
                      {t.points}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
