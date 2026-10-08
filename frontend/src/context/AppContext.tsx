import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getHealth, getMenu } from "../services/api";
import type { HealthResponse, MenuResponse } from "../types/api";
import {
  loadRecords,
  saveRecords,
  type AnalysisRecord,
} from "../services/records";

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

interface Prefs {
  theme: ThemeChoice;
  accent: AccentId;
  userName: string;
  defaultDay: string;
  defaultBand: string;
}

interface AppState {
  menu: MenuResponse | null;
  menuError: boolean;
  reloadMenu: () => void;
  health: HealthResponse | null;
  apiUp: boolean | null;
  checkHealth: () => void;
  records: AnalysisRecord[];
  addRecord: (r: AnalysisRecord) => void;
  removeRecord: (id: string) => void;
  clearRecords: () => void;
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
}

const Ctx = createContext<AppState | null>(null);

const PREFS_KEY = "nutrisense.prefs.v1";

function loadPrefs(): Prefs {
  const base: Prefs = {
    theme: "system",
    accent: "indigo",
    userName: "",
    defaultDay: "",
    defaultBand: "",
  };
  try {
    const raw = localStorage.getItem(PREFS_KEY);
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

export function AppProvider({ children }: { children: ReactNode }) {
  const [menu, setMenu] = useState<MenuResponse | null>(null);
  const [menuError, setMenuError] = useState(false);
  const [menuNonce, setMenuNonce] = useState(0);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [healthNonce, setHealthNonce] = useState(0);
  const [records, setRecords] = useState<AnalysisRecord[]>(() => loadRecords());
  const [prefs, setPrefsState] = useState<Prefs>(() => loadPrefs());

  useEffect(() => {
    getMenu()
      .then((m) => {
        setMenu(m);
        setMenuError(false);
      })
      .catch(() => {
        setMenu(null);
        setMenuError(true);
      });
  }, [menuNonce]);

  useEffect(() => {
    getHealth()
      .then((h) => {
        setHealth(h);
        setApiUp(true);
      })
      .catch(() => {
        setHealth(null);
        setApiUp(false);
      });
  }, [healthNonce]);

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

  const setPrefs = useCallback((p: Partial<Prefs>) => {
    setPrefsState((prev) => {
      const next = { ...prev, ...p };
      try {
        localStorage.setItem(PREFS_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const addRecord = useCallback((r: AnalysisRecord) => {
    setRecords((prev) => {
      const next = [r, ...prev];
      saveRecords(next);
      return next;
    });
  }, []);

  const removeRecord = useCallback((id: string) => {
    setRecords((prev) => {
      const next = prev.filter((r) => r.id !== id);
      saveRecords(next);
      return next;
    });
  }, []);

  const clearRecords = useCallback(() => {
    setRecords(() => {
      saveRecords([]);
      return [];
    });
  }, []);

  const value = useMemo<AppState>(
    () => ({
      menu,
      menuError,
      reloadMenu: () => setMenuNonce((n) => n + 1),
      health,
      apiUp,
      checkHealth: () => setHealthNonce((n) => n + 1),
      records,
      addRecord,
      removeRecord,
      clearRecords,
      prefs,
      setPrefs,
    }),
    [menu, menuError, health, apiUp, records, addRecord, removeRecord, clearRecords, prefs, setPrefs]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
