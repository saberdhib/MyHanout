import { useEffect, useState } from "react";

/**
 * Couche temps-réel isolée : polling simple (MVP). Remplaçable par des
 * websockets/SSE plus tard sans toucher aux pages qui l'utilisent.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs = 10000,
): { data: T | null; error: boolean; refresh: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    const run = () =>
      fetcher()
        .then((d) => active && (setData(d), setError(false)))
        .catch(() => active && setError(true));
    run();
    const id = setInterval(run, intervalMs);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [intervalMs, tick]);

  return { data, error, refresh: () => setTick((t) => t + 1) };
}
