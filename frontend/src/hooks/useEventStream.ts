import { useEffect, useRef, useState } from "react";
import { apiBaseUrl, currentToken } from "../api/client";

export interface StreamEvent {
  type: string;
  payload: Record<string, unknown>;
}

/**
 * Abonnement temps réel (SSE) au flux serveur `/stream/events`, filtré par
 * tenant côté backend. On passe par `fetch` (et non `EventSource`) pour pouvoir
 * envoyer le `Authorization: Bearer`. Si le flux tombe, `connected` repasse à
 * false et l'appelant retombe sur son polling de secours (usePolling).
 */
export function useEventStream(onEvent: (e: StreamEvent) => void): { connected: boolean } {
  const [connected, setConnected] = useState(false);
  const cbRef = useRef(onEvent);
  cbRef.current = onEvent;

  useEffect(() => {
    const controller = new AbortController();
    let stopped = false;

    async function connect() {
      const token = currentToken();
      if (!token) {
        // Pas encore authentifié : on réessaie un peu plus tard.
        if (!stopped) setTimeout(connect, 2000);
        return;
      }
      try {
        const resp = await fetch(`${apiBaseUrl}/stream/events`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (!resp.ok || !resp.body) throw new Error(`stream ${resp.status}`);
        setConnected(true);
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!stopped) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
            if (!dataLine) continue;
            try {
              cbRef.current(JSON.parse(dataLine.slice(5).trim()) as StreamEvent);
            } catch {
              /* heartbeat / commentaire : ignoré */
            }
          }
        }
      } catch {
        /* coupure réseau : le finally relance */
      } finally {
        setConnected(false);
        if (!stopped) setTimeout(connect, 3000); // reconnexion auto
      }
    }

    connect();
    return () => {
      stopped = true;
      controller.abort();
    };
  }, []);

  return { connected };
}
