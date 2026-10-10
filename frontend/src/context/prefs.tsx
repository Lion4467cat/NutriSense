import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AccentId, ThemeChoice } from "../hooks/useTheme";
import { useTheme } from "../hooks/useTheme";
import type { Storage } from "../services/storage";

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

  useTheme(prefs.theme, prefs.accent);

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
