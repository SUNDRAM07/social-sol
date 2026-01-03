import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const ThemeContext = createContext({ theme: 'light', setTheme: () => {} });

// Apply theme to DOM
const applyTheme = (nextTheme) => {
  const html = document.documentElement;
  const body = document.body;

  const theme = nextTheme === 'dark' ? 'dark' : 'light';
  html.setAttribute('data-theme', theme);
  body.setAttribute('data-theme', theme);

  if (theme === 'dark') {
    html.classList.add('dark');
    html.classList.remove('light');
    body.classList.add('dark');
    body.classList.remove('light');
  } else {
    html.classList.add('light');
    html.classList.remove('dark');
    body.classList.add('light');
    body.classList.remove('dark');
  }

  try {
    localStorage.setItem('theme', theme);
  } catch (_) {}
};

export function ThemeProvider({ children }) {
  // Determine initial theme (persisted -> system -> light)
  const getInitial = () => {
    try {
      const stored = localStorage.getItem('theme');
      if (stored === 'dark' || stored === 'light') return stored;
    } catch (_) {}
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  };

  const [theme, setThemeState] = useState(getInitial);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Keep in sync with system changes
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (e) => {
      const preferred = e.matches ? 'dark' : 'light';
      // Only auto-update if user hasn't explicitly chosen
      try {
        const stored = localStorage.getItem('theme');
        if (!stored) setThemeState(preferred);
      } catch (_) {
        setThemeState(preferred);
      }
    };
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, []);

  const setTheme = useCallback((next) => {
    setThemeState(next === 'dark' ? 'dark' : 'light');
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
