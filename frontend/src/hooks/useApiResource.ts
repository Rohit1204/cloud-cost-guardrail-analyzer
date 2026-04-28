"use client";

import { useCallback, useEffect, useState } from "react";

type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
};

function messageFromError(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "Request cancelled";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

export function useApiResource<T>(loader: (signal: AbortSignal) => Promise<T>, deps: unknown[] = []): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);

  useEffect(() => {
    const controller = new AbortController();

    Promise.resolve()
      .then(() => {
        if (!controller.signal.aborted) {
          setLoading(true);
          setError(null);
        }
        return loader(controller.signal);
      })
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((caught) => {
        if (controller.signal.aborted) {
          return;
        }
        setError(messageFromError(caught));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadToken, ...deps]);

  return { data, loading, error, reload };
}
