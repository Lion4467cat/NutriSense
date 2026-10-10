import { NavLink } from "react-router-dom";
import { useMenu } from "../context/menu";
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
  const statusLabel =
    apiUp === true ? "API connected" : apiUp === false ? "API unreachable" : "Connecting…";

  return (
    <aside className="sidebar" aria-label="Primary">
      <div className="sidebar-brand">
        <LogoMark />
        <div>
          <div className="brand-name">NutriSense</div>
          <div className="brand-sub">Compliance Intelligence</div>
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
            <Icon size={17} />
            {label}
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
          <IconSettings size={17} />
          Settings
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
