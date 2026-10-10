import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import type { ApiClient } from "./services/api";
import type { Storage } from "./services/storage";
import AppShell from "./layout/AppShell";
import DashboardPage from "./pages/Dashboard";
import AnalyzePage from "./pages/Analyze";
import ResultPage from "./pages/Result";
import HistoryPage from "./pages/History";
import StudentsPage from "./pages/Students";
import MenuPage from "./pages/Menu";
import AnalyticsPage from "./pages/Analytics";
import SettingsPage from "./pages/Settings";

export default function App({
  storage,
  client,
}: {
  storage: Storage;
  client: ApiClient;
}) {
  return (
    <AppProvider storage={storage} client={client}>
      <HashRouter>
        <AppShell>
          <Routes>
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
        </AppShell>
      </HashRouter>
    </AppProvider>
  );
}
