import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ApiClient } from "../services/api";
import type { HealthResponse, MenuResponse } from "../types/api";

/** The current Policy can be loading, ready, or failed — never "unknown". */
export type PolicyState = "loading" | "ready" | "failed";

interface MenuState {
  menu: MenuResponse | null;
  menuError: boolean;
  policyState: PolicyState;
  reloadMenu: () => void;
  health: HealthResponse | null;
  apiUp: boolean | null;
  checkHealth: () => void;
  client: ApiClient;
}

const Ctx = createContext<MenuState | null>(null);

export function MenuProvider({
  children,
  client,
}: {
  children: ReactNode;
  client: ApiClient;
}) {
  const [menu, setMenu] = useState<MenuResponse | null>(null);
  const [menuError, setMenuError] = useState(false);
  const [menuNonce, setMenuNonce] = useState(0);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [healthNonce, setHealthNonce] = useState(0);

  useEffect(() => {
    client
      .getMenu()
      .then((m) => {
        setMenu(m);
        setMenuError(false);
      })
      .catch(() => {
        setMenu(null);
        setMenuError(true);
      });
  }, [menuNonce, client]);

  useEffect(() => {
    client
      .getHealth()
      .then((h) => {
        setHealth(h);
        setApiUp(true);
      })
      .catch(() => {
        setHealth(null);
        setApiUp(false);
      });
  }, [healthNonce, client]);

  const value = useMemo<MenuState>(
    () => ({
      menu,
      menuError,
      policyState: menu ? "ready" : menuError ? "failed" : "loading",
      reloadMenu: () => setMenuNonce((n) => n + 1),
      health,
      apiUp,
      checkHealth: () => setHealthNonce((n) => n + 1),
      client,
    }),
    [menu, menuError, health, apiUp, client]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useMenu(): MenuState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useMenu must be used inside MenuProvider");
  return ctx;
}
