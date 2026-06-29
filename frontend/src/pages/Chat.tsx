import { useState } from "react";
import { Card } from "../components/Card";
import { sendChat, type ChatReply } from "../api/client";

type Msg = { role: "user" | "assistant"; text: string; agent?: string };

// Chat web : même cerveau (agents) que WhatsApp.
export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text) return;
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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Assistant</h1>
      <Card>
        <div className="mb-4 space-y-3" style={{ minHeight: 240 }}>
          {msgs.length === 0 && (
            <p className="text-sm text-gray-400">
              Demandez : « commande pour demain », « rupture ? », « promo samedi »…
            </p>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
              <span
                className={`inline-block rounded-card px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-brand text-white"
                    : "bg-gray-100 dark:bg-white/10"
                }`}
              >
                {m.text}
                {m.agent && (
                  <span className="ml-2 text-[10px] opacity-60">· {m.agent}</span>
                )}
              </span>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Votre message…"
            className="flex-1 rounded-card border border-gray-200 px-3 py-2 dark:bg-white/5"
          />
          <button
            onClick={send}
            disabled={busy}
            className="rounded-card bg-brand px-4 py-2 font-semibold text-white disabled:opacity-50"
          >
            Envoyer
          </button>
        </div>
      </Card>
    </div>
  );
}
