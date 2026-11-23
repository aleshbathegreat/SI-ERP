"use client";

import { createTheme, PaletteMode, ThemeOptions } from "@mui/material/styles";

function clampByte(n: number) {
  return Math.max(0, Math.min(255, Math.round(n)));
}

function lighten(hex: string, amount: number): string {
  const h = hex.replace("#", "");
  if (h.length !== 6) return hex;
  const n = parseInt(h, 16);
  const r = clampByte(((n >> 16) & 255) + amount);
  const g = clampByte(((n >> 8) & 255) + amount);
  const b = clampByte((n & 255) + amount);
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

function darken(hex: string, amount: number): string {
  return lighten(hex, -Math.abs(amount));
}

export type BrandColors = {
  primary?: string;
  secondary?: string;
};

export function getDesignTokens(mode: PaletteMode, brand?: BrandColors): ThemeOptions {
  const isDark = mode === "dark";
  const primaryBase = brand?.primary || (isDark ? "#4BA3C7" : "#0B3D5C");
  const secondaryBase = brand?.secondary || (isDark ? "#E08A5A" : "#C45C26");

  return {
    palette: {
      mode,
      primary: {
        main: primaryBase,
        light: lighten(primaryBase, isDark ? 40 : 28),
        dark: darken(primaryBase, isDark ? 20 : 24),
      },
      secondary: { main: secondaryBase },
      background: {
        default: isDark ? "#0F1419" : "#F4F7FA",
        paper: isDark ? "#171D25" : "#FFFFFF",
      },
      divider: isDark ? "rgba(255,255,255,0.12)" : "#E4EAF0",
      success: { main: isDark ? "#4CAF7A" : "#2E7D4F" },
      warning: { main: isDark ? "#D4A017" : "#B7791F" },
      error: { main: isDark ? "#F04438" : "#B42318" },
      text: {
        primary: isDark ? "#E8EEF4" : "#102033",
        secondary: isDark ? "#9AA8B6" : "#5B6B7C",
      },
    },
    typography: {
      fontFamily: '"IBM Plex Sans", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      h4: { fontWeight: 650, fontSize: "1.5rem", letterSpacing: "-0.02em" },
      h5: { fontWeight: 650, fontSize: "1.2rem" },
      h6: { fontWeight: 600, fontSize: "1.05rem" },
      subtitle1: { fontWeight: 600, fontSize: "0.95rem" },
      subtitle2: { fontWeight: 600, fontSize: "0.8125rem" },
      body2: { lineHeight: 1.45 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    shape: { borderRadius: 8 },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            transition: "background-color 0.2s ease, color 0.2s ease",
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 8, boxShadow: "none" },
          sizeSmall: { paddingInline: 12 },
        },
      },
      MuiCard: {
        defaultProps: { variant: "outlined" },
        styleOverrides: {
          root: {
            border: `1px solid ${isDark ? "rgba(255,255,255,0.10)" : "#E4EAF0"}`,
            boxShadow: "none",
            backgroundImage: "none",
          },
        },
      },
      MuiCardContent: {
        styleOverrides: {
          root: {
            padding: 20,
            "&:last-child": { paddingBottom: 20 },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 500 },
          sizeSmall: { height: 24 },
        },
      },
      MuiPaper: {
        styleOverrides: {
          outlined: {
            borderColor: isDark ? "rgba(255,255,255,0.10)" : "#E4EAF0",
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
            fontSize: "0.75rem",
            textTransform: "uppercase" as const,
            letterSpacing: "0.04em",
            color: isDark ? "#9AA8B6" : "#5B6B7C",
            backgroundColor: isDark ? "rgba(255,255,255,0.02)" : "#F8FAFC",
            borderBottomColor: isDark ? "rgba(255,255,255,0.10)" : "#E4EAF0",
            paddingTop: 12,
            paddingBottom: 12,
          },
          body: {
            fontSize: "0.875rem",
            borderBottomColor: isDark ? "rgba(255,255,255,0.06)" : "#EEF2F6",
            paddingTop: 14,
            paddingBottom: 14,
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            borderBottom: `1px solid ${isDark ? "rgba(255,255,255,0.10)" : "#E4EAF0"}`,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            borderRight: `1px solid ${isDark ? "rgba(255,255,255,0.10)" : "#E4EAF0"}`,
          },
        },
      },
    },
  };
}

export function createAppTheme(mode: PaletteMode, brand?: BrandColors) {
  return createTheme(getDesignTokens(mode, brand));
}
