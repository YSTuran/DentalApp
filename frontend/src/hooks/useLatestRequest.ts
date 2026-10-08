import { useCallback, useEffect, useRef } from "react";

export function useLatestRequest(): () => AbortController {
  const activeController = useRef<AbortController | null>(null);

  useEffect(() => () => activeController.current?.abort(), []);

  return useCallback(() => {
    activeController.current?.abort();
    const controller = new AbortController();
    activeController.current = controller;
    return controller;
  }, []);
}
