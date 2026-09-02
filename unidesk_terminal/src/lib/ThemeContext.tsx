import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

/*
  Theme (spec §5.1/§5.2): LIGHT is the default terminal surface; dark is an
  opt-in toggle. Persisted locally. Applied as [data-theme] on <html> so
  every token in index.css swaps in one place.
*/

export type Theme = "light" | "dark";

const ThemeContext = createContext<{ theme: Theme; setTheme: (t: Theme) => void }>({
  theme: "light",
  setTheme: () => {},
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() =>
    localStorage.getItem("unidesk.theme") === "dark" ? "dark" : "light",
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("unidesk.theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme: setThemeState }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
