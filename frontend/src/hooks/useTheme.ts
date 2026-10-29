import { useEffect } from "react";

export type ThemeChoice =
  | "system"
  | "light"
  | "dark"
  | "nord"
  | "rosepine"
  | "dracula"
  | "catppuccin"
  | "dawn";

export interface ThemeTileData {
  id: ThemeChoice;
  label: string;
  /** Tile-internal preview colors (bg/fg/bar/chips) — not document tokens. */
  bg: string;
  fg: string;
  accent: string;
  c1: string;
  c2: string;
  dot: string;
}

export const THEME_OPTS: ThemeTileData[] = [
  { id: "system", label: "System", bg: "linear-gradient(135deg,#f7f6fb 50%,#14131b 50%)", fg: "#45425c", accent: "#4b45c6", c1: "#15803d", c2: "#b45309", dot: "conic-gradient(#f7f6fb 0 50%, #14131b 50% 100%)" },
  { id: "light", label: "Light", bg: "#f7f6fb", fg: "#16151f", accent: "#4b45c6", c1: "#15803d", c2: "#b45309", dot: "#f7f6fb" },
  { id: "dark", label: "Dark", bg: "#14131b", fg: "#eae9f2", accent: "#8b84f0", c1: "#4ade80", c2: "#fbbf24", dot: "#14131b" },
  { id: "nord", label: "Nord", bg: "#3b4252", fg: "#eceff4", accent: "#88c0d0", c1: "#a3be8c", c2: "#ebcb8b", dot: "#2e3440" },
  { id: "rosepine", label: "Rosé Pine", bg: "#1f1d2e", fg: "#e0def4", accent: "#c4a7e7", c1: "#9ccfd8", c2: "#f6c177", dot: "#191724" },
  { id: "dracula", label: "Dracula", bg: "#2b2d3a", fg: "#f8f8f2", accent: "#bd93f9", c1: "#50fa7b", c2: "#f1fa8c", dot: "#282a36" },
  { id: "catppuccin", label: "Catppuccin", bg: "#1e1e2e", fg: "#cdd6f4", accent: "#cba6f7", c1: "#a6e3a1", c2: "#f9e2af", dot: "#1e1e2e" },
  { id: "dawn", label: "Rosé Dawn", bg: "#fffaf3", fg: "#575279", accent: "#907aa9", c1: "#286983", c2: "#ea9d34", dot: "#faf4ed" },
];

/**
 * Legacy ids (pre-consolidation themes) map into the curated seven so
 * stored prefs never render an undefined theme. Accent ids stored by
 * older builds are ignored visually: each theme now bakes its own
 * coordinated accent (the "color palette" dimension was merged into the
 * themes per the design decision).
 */
const LEGACY_THEME_MAP: Record<string, ThemeChoice> = {
  sepia: "dawn",
  midnight: "nord",
  oled: "dark",
};

export type AccentId =
  | "indigo"
  | "violet"
  | "ocean"
  | "teal"
  | "magenta"
  | "graphite"
  | "citrus"
  | "ruby";

export function resolveTheme(
  choice: ThemeChoice
): "light" | "dark" | "nord" | "rosepine" | "dracula" | "catppuccin" | "dawn" {
  if (choice !== "system") {
    return (LEGACY_THEME_MAP[choice] ?? choice) as Exclude<ThemeChoice, "system">;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

const THEME_COLORS: Record<string, string> = {
  light: "#f7f6fb",
  dark: "#14131b",
  nord: "#2e3440",
  rosepine: "#191724",
  dracula: "#282a36",
  catppuccin: "#1e1e2e",
  dawn: "#faf4ed",
};

/**
 * Apply theme (+ the legacy accent attr, ignored by tokens but kept for
 * affinity with previously stored prefs) to the document, plus the
 * theme-color meta and the system-preference listener. Called once by
 * PrefsProvider so it runs app-wide.
 */
export function useTheme(theme: ThemeChoice, accent: AccentId): void {
  useEffect(() => {
    const apply = () => {
      const resolved = resolveTheme(theme);
      document.documentElement.dataset.theme = resolved;
      document.documentElement.dataset.accent = accent;
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", THEME_COLORS[resolved] ?? "#16181c");
    };
    apply();
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme, accent]);
}
