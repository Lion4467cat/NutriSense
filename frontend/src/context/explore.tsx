import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Storage } from "../services/storage";
import {
  BADGES,
  loadExploration,
  pointsFor,
  recordVisit,
  saveExploration,
  settle,
  unlockBadge,
  type AreaId,
  type Badge,
  type BadgeId,
  type ExploreState,
} from "../explore/achievements";

interface ExploreCtx {
  state: ExploreState;
  points: number;
  /** Badges on screen right now (newest last). */
  toasts: Badge[];
  visit: (area: AreaId) => void;
  /** Grant a secret badge from a deliberate interaction. */
  discover: (id: BadgeId) => void;
  dismissToast: (id: BadgeId) => void;
  panelOpen: boolean;
  setPanelOpen: (open: boolean) => void;
  togglePanel: () => void;
}

const Ctx = createContext<ExploreCtx | null>(null);

export function ExploreProvider({
  children,
  storage,
}: {
  children: ReactNode;
  storage: Storage;
}) {
  const [state, setState] = useState<ExploreState>(() => loadExploration(storage));
  const [toasts, setToasts] = useState<BadgeId[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  // Mirrors `state` so visits (events, not renders) can compute synchronously
  // without re-subscribing effects. Kept in sync on every commit.
  const stateRef = useRef(state);
  stateRef.current = state;

  const commit = useCallback(
    (next: ExploreState, unlocked: BadgeId[]) => {
      if (next === stateRef.current) return;
      stateRef.current = next;
      setState(next);
      saveExploration(storage, next);
      if (unlocked.length > 0) {
        setToasts((prev) => [...prev, ...unlocked.filter((id) => !prev.includes(id))]);
      }
    },
    [storage]
  );

  const visit = useCallback(
    (area: AreaId) => {
      const now = new Date();
      const visited = recordVisit(stateRef.current, area, now);
      const { state: next, unlocked } = settle(visited, now);
      commit(next, unlocked);
    },
    [commit]
  );

  const discover = useCallback(
    (id: BadgeId) => {
      const next = unlockBadge(stateRef.current, id);
      commit(next, next === stateRef.current ? [] : [id]);
    },
    [commit]
  );

  const dismissToast = useCallback((id: BadgeId) => {
    setToasts((prev) => prev.filter((t) => t !== id));
  }, []);

  const togglePanel = useCallback(() => setPanelOpen((open) => !open), []);

  // Escape closes the notebook, like every other floating layer in the shell.
  useEffect(() => {
    if (!panelOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPanelOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [panelOpen]);

  const value = useMemo<ExploreCtx>(
    () => ({
      state,
      points: pointsFor(state),
      toasts: toasts.map((id) => BADGES.find((b) => b.id === id)).filter((b): b is Badge => !!b),
      visit,
      discover,
      dismissToast,
      panelOpen,
      setPanelOpen,
      togglePanel,
    }),
    [state, toasts, visit, discover, dismissToast, panelOpen, togglePanel]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useExplore(): ExploreCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useExplore must be used inside ExploreProvider");
  return ctx;
}
