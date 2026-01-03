import React, { useState, createContext, useContext, useMemo, useCallback } from 'react';

const TabsContext = createContext(null);

export function Tabs({ defaultIndex = 0, children }) {
  const [index, setIndex] = useState(defaultIndex);
  return <TabsContext.Provider value={{ index, setIndex }}>{children}</TabsContext.Provider>;
}

export function TabList({ children }) {
  return <div role="tablist" aria-orientation="horizontal" className="flex gap-2">{children}</div>;
}

export function Tab({ children, idx }) {
  const ctx = useContext(TabsContext);
  const selected = ctx.index === idx;
  return (
    <button
      role="tab"
      aria-selected={selected}
      tabIndex={selected ? 0 : -1}
      className={`px-3 py-2 rounded-md text-sm ${selected ? 'bg-[var(--brand-50)] text-[var(--brand-700)]' : 'text-[var(--text-muted)] hover:bg-[var(--bg-muted)]'}`}
      onClick={() => ctx.setIndex(idx)}
    >
      {children}
    </button>
  );
}

export function TabPanels({ children }) {
  const ctx = useContext(TabsContext);
  return <div className="mt-4">{React.Children.toArray(children)[ctx.index]}</div>;
}

export function TabPanel({ children }) {
  return <div role="tabpanel">{children}</div>;
}
