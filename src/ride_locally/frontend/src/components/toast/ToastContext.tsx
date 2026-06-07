import { createContext, useState, type ReactNode } from "react";
import { CheckCircle2, CircleX, Info, X } from "lucide-react";

type Toast = {
  id: string;
  message: string;
  variant: "success" | "error" | "info";
};

type ToastContextValue = {
  error: (message: string) => void;
  success: (message: string) => void;
  info: (message: string) => void;
};

export const ToastContext = createContext<ToastContextValue | null>(null);

function ToastIcon({ variant }: { variant: Toast["variant"] }) {
  switch (variant) {
    case "error":
      return (
        <CircleX
          className="mt-0.5 size-5 shrink-0 text-red-300"
          aria-hidden="true"
        />
      );
    case "success":
      return (
        <CheckCircle2
          className="mt-0.5 size-5 shrink-0 text-emerald-300"
          aria-hidden="true"
        />
      );
    default:
      return (
        <Info
          className="mt-0.5 size-5 shrink-0 text-teal-300"
          aria-hidden="true"
        />
      );
  }
}

function toastClasses(variant: Toast["variant"]) {
  switch (variant) {
    case "error":
      return "border-red-400/30 bg-red-500/15 text-red-50";
    case "success":
      return "border-emerald-300/30 bg-emerald-500/15 text-emerald-50";
    default:
      return "border-teal-300/30 bg-teal-500/15 text-teal-50";
  }
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  function remove(id: string) {
    setToasts((current) => current.filter((t) => t.id !== id));
  }

  function show(message: string, variant: Toast["variant"]) {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, variant }]);
    setTimeout(() => remove(id), 4000);
  }

  const value: ToastContextValue = {
    error: (message) => show(message, "error"),
    success: (message) => show(message, "success"),
    info: (message) => show(message, "info"),
  };

  return (
    <ToastContext value={value}>
      {children}

      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-3"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={[
              "pointer-events-auto rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-xl",
              toastClasses(toast.variant),
            ].join(" ")}
          >
            <div className="flex items-start gap-3">
              <ToastIcon variant={toast.variant} />

              <p className="flex-1 text-sm font-medium">{toast.message}</p>

              <button
                type="button"
                onClick={() => remove(toast.id)}
                className="shrink-0 rounded-md p-0.5 text-white/60 transition hover:bg-white/10 hover:text-white"
                aria-label="Dismiss notification"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext>
  );
}
