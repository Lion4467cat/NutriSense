import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ApiClient } from "../services/api";
import type { GoalsResponse } from "../types/api";

/**
 * GET /goals (spec 002 T-D): WHO daily-goal values for General mode, served
 * read-only like /menu. Lives in its own provider so pages that never show
 * a goal can skip it; failures leave `goals` null and the UI degrades to
 * "—" shares instead of invented numbers.
 */
interface GoalsState {
  goals: GoalsResponse | null;
  goalsError: boolean;
  reloadGoals: () => void;
  client: ApiClient;
}

const Ctx = createContext<GoalsState | null>(null);

export function GoalsProvider({
  children,
  client,
}: {
  children: ReactNode;
  client: ApiClient;
}) {
  const [goals, setGoals] = useState<GoalsResponse | null>(null);
  const [goalsError, setGoalsError] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    client
      .getGoals()
      .then((g) => {
        setGoals(g);
        setGoalsError(false);
      })
      .catch(() => {
        setGoals(null);
        setGoalsError(true);
      });
  }, [nonce, client]);

  const value = useMemo<GoalsState>(
    () => ({
      goals,
      goalsError,
      reloadGoals: () => setNonce((n) => n + 1),
      client,
    }),
    [goals, goalsError, client]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useGoals(): GoalsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useGoals must be used inside GoalsProvider");
  return ctx;
}
