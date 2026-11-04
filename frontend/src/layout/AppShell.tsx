import { useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion, useMotionValue, useSpring } from "framer-motion";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import DiscoverPanel from "../ui/DiscoverPanel";
import AchievementToasts from "../ui/AchievementToasts";
import { useExplore } from "../context/explore";
import { areaForPath, detectSecret } from "../explore/achievements";
import { IS_DEMO_MODE } from "../services/mode";

export default function AppShell({ children }: { children: ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { visit, discover } = useExplore();
  const mainRef = useRef<HTMLElement>(null);

  // Reading-position rail: the accent line under the topbar tracks how far
  // through a page you are. The app scrolls the window in the compact bar
  // layout and .main on shorter pages, so the rail measures whichever one
  // actually overflows. Spring-smoothed so it glides instead of jitters.
  const progress = useMotionValue(0);
  const rail = useSpring(progress, { stiffness: 200, damping: 32, mass: 0.3 });

  useEffect(() => {
    const main = mainRef.current;
    const measure = () => {
      const inner = main && main.scrollHeight > main.clientHeight + 1;
      const scrolled = inner ? main!.scrollTop : window.scrollY;
      const total = inner
        ? main!.scrollHeight - main!.clientHeight
        : document.documentElement.scrollHeight - window.innerHeight;
      progress.set(total > 0 ? Math.min(1, Math.max(0, scrolled / total)) : 0);
    };
    measure();
    window.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    main?.addEventListener("scroll", measure, { passive: true });
    return () => {
      window.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
      main?.removeEventListener("scroll", measure);
    };
  }, [progress, location.pathname]);

  useEffect(() => {
    setDrawer(false);
    const main = document.querySelector(".main");
    if (main) main.scrollTo({ top: 0 });
    // A new section starts at its own top; CSS smooth scrolling is bypassed
    // so the page transition and the scroll reset do not fight each other.
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    // Every route is an exploration event; the provider decides what, if
    // anything, it unlocks. Result views count as history.
    visit(areaForPath(location.pathname));
  }, [location.pathname, visit]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawer(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // Secret keystrokes. Ignored inside fields and whenever a modifier is
  // held, so normal typing, shortcuts and screen-reader navigation are
  // untouched. The detector module owns the actual sequences.
  useEffect(() => {
    let buffer: string[] = [];
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      if (target?.closest?.("input, textarea, select, [contenteditable='true']")) return;
      const result = detectSecret(buffer, e.key);
      buffer = result.buffer;
      if (result.secret) discover(result.secret);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [discover]);

  return (
    <div className={`shell${drawer ? " drawer-open" : ""}`}>
      <motion.div
        className="scroll-rail"
        style={{ scaleX: rail }}
        aria-hidden="true"
      />
      <Sidebar onNavigate={() => setDrawer(false)} />
      <div
        className="drawer-backdrop"
        onClick={() => setDrawer(false)}
        aria-hidden="true"
      />
      <Topbar drawerOpen={drawer} onToggleDrawer={() => setDrawer((open) => !open)} />
      <main className="main" id="main" ref={mainRef}>
        {IS_DEMO_MODE && (
          <div className="demo-mode-banner" role="status">
            <strong>Demo mode</strong>
            <span>Fixed sample results are shown. Uploaded pixels are not analyzed and no ML models are loaded.</span>
          </div>
        )}
        {children}
      </main>
      <AchievementToasts />
      <DiscoverPanel />
    </div>
  );
}

/** Small helper so pages can deep-link with router without prop drilling. */
export function useGo() {
  const navigate = useNavigate();
  return (to: string) => navigate(to);
}
