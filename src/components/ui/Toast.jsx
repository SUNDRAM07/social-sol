import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((toast) => {
    const id = Date.now().toString();
    const t = { id, ...toast };
    setToasts((s) => [t, ...s]);
    if (toast.duration !== 0) {
      setTimeout(() => {
        setToasts((s) => s.filter((x) => x.id !== id));
      }, toast.duration || 4000);
    }
    return id;
  }, []);

  const remove = useCallback((id) => setToasts((s) => s.filter((t) => t.id !== id)), []);

  const value = useMemo(() => ({ push, remove }), [push, remove]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} role="status" className="p-3 rounded-md shadow-md bg-[var(--surface)] border border-[var(--border)]">
            <div className="font-medium">{t.title}</div>
            {t.description && <div className="text-sm text-[var(--text-muted)]">{t.description}</div>}
            <div className="text-xs text-[var(--text-muted)] mt-2">{t.timestamp && new Date(t.timestamp).toLocaleTimeString()}</div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
