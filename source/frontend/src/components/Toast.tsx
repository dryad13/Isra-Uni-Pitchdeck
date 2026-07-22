import { createContext, useCallback, useContext, useEffect, useState } from "react";

type ToastAppearance = "success" | "error" | "info";

type ToastItem = {
  id: number;
  message: string;
  appearance: ToastAppearance;
};

type ToastContextValue = {
  toast: (message: string, appearance?: ToastAppearance) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, appearance: ToastAppearance = "success") => {
      const id = ++nextId;
      setToasts((prev) => [...prev, { id, message, appearance }]);
      if (appearance !== "error") {
        window.setTimeout(() => dismiss(id), 4000);
      }
    },
    [dismiss],
  );

  const value: ToastContextValue = {
    toast,
    success: (m) => toast(m, "success"),
    error: (m) => toast(m, "error"),
    info: (m) => toast(m, "info"),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <ToastMessage key={t.id} item={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastMessage({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  useEffect(() => {
    if (item.appearance === "error") return;
    const prefersReduced =
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;
  }, [item.appearance]);

  return (
    <div className={`toast toast-${item.appearance}`} role="alert">
      <span>{item.message}</span>
      <button type="button" className="toast-dismiss" onClick={onDismiss} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
