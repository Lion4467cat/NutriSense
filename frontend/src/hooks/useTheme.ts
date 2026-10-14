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

export const THEME_OPTS: {
  id: ThemeChoice;
  label: string;
  dot: string;
}[] = [
  { id: "system", label: "System", dot: "conic-gradient(#f6f5f2 0 50%, #16181c 50% 100%)" },
  { id: "light", label: "Light", dot: "#faf9f7" },
  { id: "dark", label: "Dark", dot: "#16181c" },
  { id: "nord", label: "Nord", dot: "#2e3440" },
  { id: "rosepine", label: "Rosé Pine", dot: "#191724" },
  { id: "dracula", label: "Dracula", dot: "#282a36" },
  { id: "catppuccin", label: "Catppuccin", dot: "#1e1e2e" },
  { id: "dawn", label: "Rosé Dawn", dot: "#faf4ed" },
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
  light: "#faf9f7",
  dark: "#0e0f11",
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
