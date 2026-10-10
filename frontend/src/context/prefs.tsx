import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Storage } from "../services/storage";

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

export interface Prefs {
  theme: ThemeChoice;
  accent: AccentId;
  userName: string;
  defaultDay: string;
  defaultBand: string;
}

export const PREFS_KEY = "nutrisense.prefs.v1";

function loadPrefs(storage: Storage): Prefs {
  const base: Prefs = {
    theme: "system",
    accent: "indigo",
    userName: "",
    defaultDay: "",
    defaultBand: "",
  };
  try {
    const raw = storage.get(PREFS_KEY);
    if (raw) return { ...base, ...(JSON.parse(raw) as Partial<Prefs>) };
  } catch {
    /* ignore */
  }
  return base;
}

function resolveTheme(
  choice: ThemeChoice
): "light" | "dark" | "sepia" | "midnight" | "oled" {
  if (choice !== "system") return choice;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

interface PrefsState {
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
}

const Ctx = createContext<PrefsState | null>(null);

export function PrefsProvider({
  children,
  storage,
}: {
  children: ReactNode;
  storage: Storage;
}) {
  const [prefs, setPrefsState] = useState<Prefs>(() => loadPrefs(storage));

  useEffect(() => {
    const apply = () => {
      const resolved = resolveTheme(prefs.theme);
      document.documentElement.dataset.theme = resolved;
      document.documentElement.dataset.accent = prefs.accent;
      const meta = document.querySelector('meta[name="theme-color"]');
      const colors: Record<string, string> = {
        light: "#faf9f7",
        sepia: "#f6efe2",
        dark: "#0e0f11",
        midnight: "#0a0e1a",
        oled: "#000000",
      };
      if (meta) meta.setAttribute("content", colors[resolved]);
    };
    apply();
    if (prefs.theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [prefs.theme, prefs.accent]);

  const setPrefs = useCallback(
    (p: Partial<Prefs>) => {
      setPrefsState((prev) => {
        const next = { ...prev, ...p };
        try {
          storage.set(PREFS_KEY, JSON.stringify(next));
        } catch {
          /* ignore */
        }
        return next;
      });
    },
    [storage]
  );

  const value = useMemo<PrefsState>(
    () => ({ prefs, setPrefs }),
    [prefs, setPrefs]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePrefs(): PrefsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePrefs must be used inside PrefsProvider");
  return ctx;
}
