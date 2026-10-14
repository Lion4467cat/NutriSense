import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import { HashRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import type { ApiClient } from "./services/api";
import type { Storage } from "./services/storage";
import AppShell from "./layout/AppShell";
import { pageTransition, pageVariants } from "./ui/motion";
import DashboardPage from "./pages/Dashboard";
import AnalyzePage from "./pages/Analyze";
import ResultPage from "./pages/Result";
import HistoryPage from "./pages/History";
import StudentsPage from "./pages/Students";
import MenuPage from "./pages/Menu";
import AnalyticsPage from "./pages/Analytics";
import SettingsPage from "./pages/Settings";

/**
 * Route transitions (wave 1): AnimatePresence keyed by pathname, so the
 * outgoing page exits before the incoming one enters (mode="wait").
 * reducedMotion="user" (MotionConfig above) means prefers-reduced-motion
 * users see opacity-only fades — framer neutralizes the transforms.
 */
function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        className="route-anim"
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={pageTransition}
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
    </AnimatePresence>
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
          <AppShell>
            <AnimatedRoutes />
          </AppShell>
        </HashRouter>
      </MotionConfig>
    </AppProvider>
  );
}
