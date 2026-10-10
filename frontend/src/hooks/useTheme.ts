import { useEffect } from "react";

export type ThemeChoice =
  | "light"
  | "dark"
  | "system"
  | "sepia"
  | "midnight"
  | "oled";

export const THEME_OPTS: {
  id: ThemeChoice;
  label: string;
  dot: string;
}[] = [
  { id: "light", label: "Light", dot: "#f6f5f2" },
  { id: "dark", label: "Dark", dot: "#16181c" },
  { id: "sepia", label: "Sepia", dot: "#efe2c6" },
  { id: "midnight", label: "Midnight", dot: "#0a0e1a" },
  { id: "oled", label: "OLED", dot: "#000000" },
  {
    id: "system",
    label: "System",
    dot: "conic-gradient(#f6f5f2 0 50%, #16181c 50% 100%)",
  },
];

export type AccentId =
  | "indigo"
  | "violet"
  | "ocean"
  | "teal"
  | "magenta"
  | "graphite";

export const ACCENTS: { id: AccentId; label: string; swatch: string }[] = [
  { id: "indigo", label: "Indigo", swatch: "#4f46e5" },
  { id: "violet", label: "Violet", swatch: "#7c3aed" },
  { id: "ocean", label: "Ocean", swatch: "#0369a1" },
  { id: "teal", label: "Teal", swatch: "#0f766e" },
  { id: "magenta", label: "Magenta", swatch: "#be185d" },
  { id: "graphite", label: "Graphite", swatch: "#475569" },
];

export function resolveTheme(
  choice: ThemeChoice
): "light" | "dark" | "sepia" | "midnight" | "oled" {
  if (choice !== "system") return choice;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

const THEME_COLORS: Record<string, string> = {
  light: "#faf9f7",
  sepia: "#f6efe2",
  dark: "#0e0f11",
  midnight: "#0a0e1a",
  oled: "#000000",
};

/**
 * Apply theme + accent to the document (data-theme/data-accent, theme-color
 * meta, system-preference listener). Called once by PrefsProvider so it runs
 * app-wide regardless of which page is mounted.
 */
export function useTheme(theme: ThemeChoice, accent: AccentId): void {
  useEffect(() => {
    const apply = () => {
      const resolved = resolveTheme(theme);
      document.documentElement.dataset.theme = resolved;
      document.documentElement.dataset.accent = accent;
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", THEME_COLORS[resolved]);
    };
    apply();
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme, accent]);
}
