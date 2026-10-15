import { useCallback, useEffect, useRef, useState } from 'react';

// Runs an async loader on mount (and when deps change), optionally polling.
// Keeps the previous data on screen during background refreshes and failed polls.
export function useApi(loader, deps = [], { interval } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const requestId = useRef(0);

  const load = useCallback(async (silent = false) => {
    const id = ++requestId.current;
    if (!silent) setState((s) => ({ ...s, loading: true }));
    try {
      const data = await loaderRef.current();
      if (id === requestId.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (id === requestId.current) setState((s) => ({ data: s.data, error, loading: false }));
    }
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!interval) return undefined;
    const timer = setInterval(() => load(true), interval);
    return () => clearInterval(timer);
  }, [interval, load]);

  return { ...state, reload: load };
}
