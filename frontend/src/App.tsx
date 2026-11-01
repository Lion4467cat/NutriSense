import { MotionConfig, motion, type Variants } from "framer-motion";
import { useEffect, useRef } from "react";
import { HashRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import { OnboardingProvider } from "./context/onboarding";
import type { ApiClient } from "./services/api";
import type { Storage } from "./services/storage";
import AppShell from "./layout/AppShell";
import { EASE } from "./ui/motion";
import { areaDepth } from "./explore/achievements";
import DashboardPage from "./pages/Dashboard";
import AnalyzePage from "./pages/Analyze";
import ResultPage from "./pages/Result";
import HistoryPage from "./pages/History";
import StudentsPage from "./pages/Students";
import MenuPage from "./pages/Menu";
import AnalyticsPage from "./pages/Analytics";
import SettingsPage from "./pages/Settings";

/**
 * Route transitions (wave 4): the page enters from the direction you are
 * already travelling — from the right when you move down the nav order, from
 * the left when you go back up — so a section change reads as movement
 * through a space rather than a hard cut. `custom` carries that direction
 * into the variant function.
 *
 * reducedMotion="user" (MotionConfig above) means prefers-reduced-motion
 * users see opacity-only fades: framer neutralizes the transform.
 */
const slideVariants: Variants = {
  initial: (dir: number) => ({ opacity: 0, x: dir * 26 }),
  animate: { opacity: 1, x: 0, transition: { duration: 0.3, ease: EASE } },
};

function AnimatedRoutes() {
  const location = useLocation();
  const lastPath = useRef(location.pathname);
  const dir =
    areaDepth(location.pathname) >= areaDepth(lastPath.current) ? 1 : -1;

  useEffect(() => {
    lastPath.current = location.pathname;
  }, [location.pathname]);

  return (
    // Enter-only on purpose: a keyed remount starts the slide the instant the
    // route changes. An exit phase (AnimatePresence mode="wait") held the new
    // page back by most of a second on this app, which read as a hang.
    <motion.div
      key={location.pathname}
      className="route-anim"
      custom={dir}
      variants={slideVariants}
      initial="initial"
      animate="animate"
    >
      <Routes location={location}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/result/:id" element={<ResultPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/students/:name" element={<StudentsPage />} />
        <Route path="/menu" element={<MenuPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </motion.div>
  );
}

export default function App({
  storage,
  client,
}: {
  storage: Storage;
  client: ApiClient;
}) {
  return (
    <AppProvider storage={storage} client={client}>
      <MotionConfig reducedMotion="user">
        <HashRouter>
          {/* First-run profile wizard: mounted at the root so Settings can
              re-open it and the flag persists through the prefs storage. */}
          <OnboardingProvider>
            <AppShell>
              <AnimatedRoutes />
            </AppShell>
          </OnboardingProvider>
        </HashRouter>
      </MotionConfig>
    </AppProvider>
  );
}
