import { useState } from "react";
import { sendChat, type ChatReply } from "../api/client";

type Msg = { role: "user" | "assistant"; text: string; agent?: string };

/**
 * Fenêtre de chat flottante, accessible depuis **toutes** les pages : l'utilisateur
 * demande directement ce qu'il veut (même cerveau d'agents que WhatsApp/Slack).
 * Bulle en bas à droite → ouvre/ferme le panneau.
 */
export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const r: ChatReply = await sendChat(text);
      setMsgs((m) => [...m, { role: "assistant", text: r.reply, agent: r.agent }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", text: "Erreur (API injoignable)." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {/* Bulle flottante */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Ouvrir le chat"
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-brand text-2xl text-white shadow-card transition-transform hover:scale-105"
      >
        {open ? "✕" : "💬"}
      </button>

      {/* Fenêtre de chat */}
      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[28rem] w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-xl2 border border-night/10 bg-white shadow-card dark:border-white/10 dark:bg-night">
          <div className="flex items-center justify-between bg-brand px-4 py-3 text-white">
            <span className="font-semibold">Assistant MyHanout</span>
            <span className="text-[11px] opacity-80">demandez ce que vous voulez</span>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {msgs.length === 0 && (
              <p className="text-sm text-night/40 dark:text-surface/40">
                Ex. « commande pour demain », « rupture ? », « promo samedi », « marge du
                poulet »…
              </p>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                <span
                  className={`inline-block max-w-[85%] rounded-card px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-brand text-white"
                      : "bg-night/[0.06] dark:bg-white/10"
                  }`}
                >
                  {m.text}
                  {m.agent && <span className="ml-2 text-[10px] opacity-60">· {m.agent}</span>}
                </span>
              </div>
            ))}
            {busy && <div className="text-left text-xs text-night/40">…</div>}
          </div>

          <div className="flex gap-2 border-t border-night/10 p-2 dark:border-white/10">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Votre message…"
              className="flex-1 rounded-card border border-night/15 px-3 py-2 text-sm dark:border-white/15 dark:bg-white/5"
            />
            <button
              onClick={send}
              disabled={busy}
              className="rounded-card bg-brand px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  );
}
