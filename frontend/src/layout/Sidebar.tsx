import { NavLink } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { useMenu } from "../context/menu";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { apiBase } from  "../services/api";
import {
  IconBook,
  IconCamera,
  IconChart,
  IconDashboard,
  IconHistory,
  IconSettings,
  IconUsers,
  LogoMark,
} from  "../ui/Icon";

const NAV = [
  { to: "/", label: "Dashboard", icon: IconDashboard, end: true },
  { to: "/analyze", label: "Analyze Meal", icon: IconCamera },
  { to: "/history", label: "Analysis History", icon: IconHistory },
  { to: "/students", label: "Student Records", icon: IconUsers },
  { to: "/menu", label: "Menu & Standards", icon: IconBook },
  { to: "/analytics", label: "Analytics", icon: IconChart },
];

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { apiUp, menu } = useMenu();
  const { records } = useRecords();
  const { prefs } = usePrefs();
  const { pathname } = useLocation();
  const general = (prefs.mode ?? "school") === "general";
  const isActive = (to: string, end?: boolean) =>
    end ? pathname === to : pathname.startsWith(to);
  const statusLabel =
    apiUp === true ? "API connected" : apiUp === false ? "API unreachable" : "Connecting…";

  return (
    <aside className="sidebar" aria-label="Primary">
      <div className="sidebar-brand">
        <LogoMark />
        <div>
          <div className="brand-name">NutriSense</div>
          <div className="brand-sub">
            {general ? "Daily goal tracking" : "Compliance Intelligence"}
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">Workspace</div>
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            onClick={onNavigate}
          >
            {isActive(to, end) && (
              <motion.span
                className="nav-glider"
                layoutId="nav-glider"
                transition={{ type: "spring", stiffness: 480, damping: 38 }}
                aria-hidden="true"
              />
            )}
            <Icon size={17} />
            <span>{label}</span>
            {to === "/history" && records.length > 0 && (
              <span className="nav-badge num">{records.length}</span>
            )}
            {to === "/menu" && menu && (
              <span className="nav-badge num">{Object.keys(menu.dishes).length}</span>
            )}
          </NavLink>
        ))}

        <div className="nav-section">System</div>
        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          onClick={onNavigate}
        >
          {isActive("/settings", true) && (
            <motion.span
              className="nav-glider"
              layoutId="nav-glider"
              transition={{ type: "spring", stiffness: 480, damping: 38 }}
              aria-hidden="true"
            />
          )}
          <IconSettings size={17} />
          <span>Settings</span>
        </NavLink>
      </nav>

      <div className="sidebar-foot">
        <div className="api-status" title={`${statusLabel} — ${apiBase}`}>
          <span
            className={`dot ${apiUp === true ? "up" : apiUp === false ? "down" : "unknown"}`}
            aria-hidden="true"
          />
          {statusLabel}
        </div>
        <div className="api-endpoint" title={`Connected backend: ${apiBase}`}>
          {apiBase.replace(/^https?:\/\//, "")}
        </div>
        <div className="workspace">
          <span className="avatar" aria-hidden="true">
            NM
          </span>
          <div>
            <div className="workspace-name">NutriSense Monitor</div>
            <div className="workspace-role">Local workspace</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
