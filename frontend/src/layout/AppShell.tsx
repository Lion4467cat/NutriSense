import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppShell({ children }: { children: ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { prefs, setPrefs } = useApp();

  useEffect(() => {
    setDrawer(false);
    const main = document.querySelector(".main");
    if (main) main.scrollTo({ top: 0 });
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawer(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const toggleTheme = () => {
    const current = document.documentElement.dataset.theme;
    const darkish = current === "dark" || current === "midnight" || current === "oled";
    setPrefs({ theme: darkish ? "light" : "dark" });
  };

  return (
    <div className={`shell${drawer ? " drawer-open" : ""}`}>
      <Sidebar onNavigate={() => setDrawer(false)} />
      <div
        className="drawer-backdrop"
        onClick={() => setDrawer(false)}
        aria-hidden="true"
      />
      <Topbar onOpenDrawer={() => setDrawer(true)} onToggleTheme={toggleTheme} />
      <main className="main" id="main">
        {children}
      </main>
    </div>
  );
}

/** Small helper so pages can deep-link with router without prop drilling. */
export function useGo() {
  const navigate = useNavigate();
  return (to: string) => navigate(to);
}
