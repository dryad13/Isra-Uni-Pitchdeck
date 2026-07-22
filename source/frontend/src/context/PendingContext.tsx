import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../lib/api";

type PendingContextValue = {
  pending: number;
  refreshPending: () => Promise<void>;
};

const PendingContext = createContext<PendingContextValue | null>(null);

export function PendingProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = useState(0);
  const location = useLocation();

  const refreshPending = useCallback(async () => {
    try {
      const data = await api<{ items: unknown[] }>("/verification/pending");
      setPending(data.items.length);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refreshPending();
    const id = window.setInterval(refreshPending, 10_000);
    return () => window.clearInterval(id);
  }, [refreshPending, location.pathname]);

  return (
    <PendingContext.Provider value={{ pending, refreshPending }}>
      {children}
    </PendingContext.Provider>
  );
}

export function usePending() {
  const ctx = useContext(PendingContext);
  if (!ctx) throw new Error("usePending must be used within PendingProvider");
  return ctx;
}
