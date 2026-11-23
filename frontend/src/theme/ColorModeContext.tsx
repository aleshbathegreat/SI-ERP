"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { PaletteMode, ThemeProvider } from "@mui/material";
import CssBaseline from "@mui/material/CssBaseline";
import { BrandColors, createAppTheme } from "./theme";

type ColorModeContextValue = {
  mode: PaletteMode;
  toggleColorMode: () => void;
  setMode: (mode: PaletteMode) => void;
};

type BrandThemeContextValue = {
  brandColors: BrandColors;
  setBrandColors: (c: BrandColors) => void;
};

const ColorModeContext = createContext<ColorModeContextValue>({
  mode: "light",
  toggleColorMode: () => undefined,
  setMode: () => undefined,
});

const BrandThemeContext = createContext<BrandThemeContextValue>({
  brandColors: {},
  setBrandColors: () => undefined,
});

const STORAGE_KEY = "sigbl_color_mode";

function resolveInitialMode(): PaletteMode {
  if (typeof window === "undefined") return "light";
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "light" || saved === "dark") return saved;
  if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) return "dark";
  return "light";
}

export function ColorModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<PaletteMode>("light");
  const [ready, setReady] = useState(false);
  const [brandColors, setBrandColorsState] = useState<BrandColors>({});

  useEffect(() => {
    setModeState(resolveInitialMode());
    setReady(true);
  }, []);

  const setMode = useCallback((next: PaletteMode) => {
    setModeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.setAttribute("data-color-mode", next);
  }, []);

  const toggleColorMode = useCallback(() => {
    setModeState((prev) => {
      const next = prev === "light" ? "dark" : "light";
      localStorage.setItem(STORAGE_KEY, next);
      document.documentElement.setAttribute("data-color-mode", next);
      return next;
    });
  }, []);

  const setBrandColors = useCallback((c: BrandColors) => {
    setBrandColorsState((prev) => {
      if (prev.primary === c.primary && prev.secondary === c.secondary) return prev;
      return c;
    });
  }, []);

  useEffect(() => {
    if (!ready) return;
    document.documentElement.setAttribute("data-color-mode", mode);
  }, [mode, ready]);

  const theme = useMemo(() => createAppTheme(mode, brandColors), [mode, brandColors]);

  const colorValue = useMemo(
    () => ({ mode, toggleColorMode, setMode }),
    [mode, toggleColorMode, setMode]
  );

  const brandValue = useMemo(
    () => ({ brandColors, setBrandColors }),
    [brandColors, setBrandColors]
  );

  return (
    <ColorModeContext.Provider value={colorValue}>
      <BrandThemeContext.Provider value={brandValue}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </BrandThemeContext.Provider>
    </ColorModeContext.Provider>
  );
}

export function useColorMode() {
  return useContext(ColorModeContext);
}

export function useBrandTheme() {
  return useContext(BrandThemeContext);
}
