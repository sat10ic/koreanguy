import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";

/*
  E-4: the toast system — the acknowledgment layer the app never had (the
  Desk register changed state with zero visual feedback). Animations come
  from framer-motion and respect the OS reduced-motion setting through
  MotionConfig (main.tsx) on top of the CSS prefers-reduced-motion block.
*/

export type ToastTone = "success" | "error" | "info";
export interface Toast {
  id: number;
  tone: ToastTone;
  title: string;
  detail?: string;
}

const ToastContext = createContext<{ push: (t: Omit<Toast, "id">) => void }>({
  push: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const seq = useRef(0);

  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = ++seq.current;
    setToasts((list) => [...list, { ...t, id }]);
    setTimeout(() => setToasts((list) => list.filter((x) => x.id !== id)), 6000);
  }, []);

  const dismiss = (id: number) => setToasts((list) => list.filter((x) => x.id !== id));

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} role="status"
            className={"pointer-events-auto flex items-start gap-2 rounded-card border px-3 py-2.5 text-caption shadow-lg " +
              (t.tone === "success" ? "border-positive-border bg-positive-bg text-ink-primary"
                : t.tone === "error" ? "border-danger-border bg-danger-bg text-ink-primary"
                  : "border-border bg-surface-1 text-ink-primary")}>
            {t.tone === "success" ? <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-positive" aria-hidden />
              : t.tone === "error" ? <AlertTriangle size={14} className="mt-0.5 shrink-0 text-danger" aria-hidden />
                : null}
            <div className="min-w-0 flex-1">
              <div className="font-semibold">{t.title}</div>
              {t.detail && <div className="mt-0.5 break-words text-ink-secondary">{t.detail}</div>}
            </div>
            <button aria-label="Dismiss" onClick={() => dismiss(t.id)} className="shrink-0 text-ink-tertiary hover:text-ink-secondary">
              <X size={13} aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
