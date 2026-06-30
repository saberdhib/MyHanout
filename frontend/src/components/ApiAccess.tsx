import { useEffect, useState } from "react";
import { Card } from "./Card";
import {
  createApiKey,
  createWebhook,
  deleteWebhook,
  listApiKeys,
  listWebhooks,
  revokeApiKey,
  type ApiKey,
  type Webhook,
} from "../api/client";

/**
 * Ouverture : gestion des clés API (accès programmatique n8n/Make/Zapier) et des
 * webhooks sortants. La clé et le secret ne sont montrés qu'une fois (à la création).
 */
export default function ApiAccess() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [hooks, setHooks] = useState<Webhook[]>([]);
  const [keyName, setKeyName] = useState("");
  const [hookUrl, setHookUrl] = useState("");
  const [reveal, setReveal] = useState<string | null>(null); // clé/secret affiché une fois

  async function refresh() {
    const [k, w] = await Promise.all([listApiKeys(), listWebhooks()]);
    setKeys(k.items);
    setHooks(w.items);
  }
  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function addKey(e: React.FormEvent) {
    e.preventDefault();
    if (!keyName.trim()) return;
    const created = await createApiKey(keyName.trim());
    setKeyName("");
    setReveal(`Clé API « ${created.name} » : ${created.key}`);
    refresh();
  }
  async function addHook(e: React.FormEvent) {
    e.preventDefault();
    if (!hookUrl.trim()) return;
    const created = await createWebhook(hookUrl.trim());
    setHookUrl("");
    setReveal(`Webhook ${created.url} — secret de signature : ${created.secret}`);
    refresh();
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {reveal && (
        <div className="lg:col-span-2 rounded-card border border-brand/30 bg-brand/10 p-3 text-sm">
          <strong>À copier maintenant (affiché une seule fois) :</strong>
          <div className="mt-1 break-all font-mono text-xs">{reveal}</div>
        </div>
      )}

      <Card title="Clés API" subtitle="Accès programmatique (n8n, Make, Zapier, scripts)">
        <form onSubmit={addKey} className="flex gap-2">
          <input
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            placeholder="Nom (ex. n8n prod)"
            className="flex-1 rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
          <button className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white">
            Créer
          </button>
        </form>
        <ul className="mt-3 space-y-2 text-sm">
          {keys.map((k) => (
            <li key={k.id} className="flex items-center justify-between gap-2">
              <span>
                <span className="font-mono text-xs">{k.prefix}…</span> · {k.name}
                {k.revoked && <span className="ml-2 text-rose-500">révoquée</span>}
              </span>
              {!k.revoked && (
                <button
                  onClick={() => revokeApiKey(k.id).then(refresh)}
                  className="text-xs text-rose-600 hover:underline"
                >
                  Révoquer
                </button>
              )}
            </li>
          ))}
          {keys.length === 0 && (
            <li className="text-night/40 dark:text-surface/40">Aucune clé.</li>
          )}
        </ul>
        <p className="mt-3 text-xs text-night/50 dark:text-surface/50">
          Header <code>X-API-Key: &lt;clé&gt;</code> sur l'API (<code>/api/v1/...</code>).
        </p>
      </Card>

      <Card title="Webhooks sortants" subtitle="MyHanout POSTe ses événements (signés HMAC)">
        <form onSubmit={addHook} className="flex gap-2">
          <input
            value={hookUrl}
            onChange={(e) => setHookUrl(e.target.value)}
            placeholder="URL (n8n / Make / Zapier)"
            className="flex-1 rounded-card border border-night/15 px-2 py-1.5 text-sm dark:border-white/15 dark:bg-white/5"
          />
          <button className="rounded-card bg-brand px-3 py-1.5 text-sm font-semibold text-white">
            Ajouter
          </button>
        </form>
        <ul className="mt-3 space-y-2 text-sm">
          {hooks.map((w) => (
            <li key={w.id} className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate">
                <span className="truncate">{w.url}</span>{" "}
                <span className="text-night/40 dark:text-surface/40">({w.events})</span>
              </span>
              <button
                onClick={() => deleteWebhook(w.id).then(refresh)}
                className="text-xs text-rose-600 hover:underline"
              >
                Supprimer
              </button>
            </li>
          ))}
          {hooks.length === 0 && (
            <li className="text-night/40 dark:text-surface/40">Aucun webhook.</li>
          )}
        </ul>
        <p className="mt-3 text-xs text-night/50 dark:text-surface/50">
          Événements : <code>alert_created</code>, <code>pipeline_finished</code>… ·
          signature <code>X-MyHanout-Signature</code>.
        </p>
      </Card>
    </div>
  );
}
