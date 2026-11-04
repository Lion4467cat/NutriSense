import { useRef } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { introItem, introStagger } from "../ui/motion";
import { ProgressRing } from "../ui/fx";
import { useMenu } from "../context/menu";
import { useRecords } from "../context/records";
import { useExplore } from "../context/explore";
import { TOTAL_AREAS, exploredCount, pointsFor } from "../explore/achievements";
import { apiBase } from "../services/api";
import {
  IconSettings,
  IconX,
  LogoMark,
} from "../ui/Icon";
import { NAV_ITEMS } from "./Topbar";

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { apiUp, menu } = useMenu();
  const { records } = useRecords();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { state, panelOpen, togglePanel, discover } = useExplore();
  const explored = exploredCount(state);
  const points = pointsFor(state);
  // Brand easter egg: five taps in quick succession.
  const taps = useRef<number[]>([]);
  const TAP_WINDOW_MS = 2600;

  const isActive = (to: string, end?: boolean) =>
    end ? pathname === to : pathname.startsWith(to);
  const statusLabel =
    apiUp === true ? "API connected" : apiUp === false ? "API unreachable" : "Connecting…";

  return (
    <motion.aside
      className="sidebar"
      aria-label="Mobile navigation drawer"
      variants={introStagger}
      initial="hidden"
      animate="show"
    >
      <div className="sidebar-brand">
        <button
          type="button"
          className="brand-link"
          aria-label="NutriSense — go home"
          onClick={() => {
            const now = Date.now();
            taps.current = [...taps.current, now].filter((t) => now - t < TAP_WINDOW_MS);
            if (taps.current.length >= 5) {
              taps.current = [];
              discover("logo-patter");
            }
            navigate("/");
            onNavigate?.();
          }}
        >
          <LogoMark />
          <div>
            <div className="brand-name">NutriSense</div>
            <div className="brand-sub">Meal intelligence</div>
          </div>
        </button>
        <button
          type="button"
          className="icon-btn drawer-close"
          onClick={onNavigate}
          aria-label="Close navigation drawer"
          title="Close drawer"
        >
          <IconX size={18} />
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <motion.div
            key={to}
            variants={introItem}
            whileTap={{ scale: 0.95 }}
          >
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
              onClick={onNavigate}
              title={label}
            >
              <Icon size={17} />
              <span>{label}</span>
              {to === "/history" && records.length > 0 && (
                <span className="nav-badge num">{records.length}</span>
              )}
              {to === "/menu" && menu && Object.keys(menu.dishes).length > 0 && (
                <span className="nav-badge num">
                  {Object.keys(menu.dishes).length}
                </span>
              )}
            </NavLink>
          </motion.div>
        ))}

        <motion.div
          key="/settings"
          variants={introItem}
          whileTap={{ scale: 0.95 }}
        >
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            onClick={onNavigate}
            title="Settings & preferences"
          >
            <IconSettings size={17} />
            <span>Settings & preferences</span>
          </NavLink>
        </motion.div>
      </nav>

      <div className="sidebar-foot">
        <button
          type="button"
          className={`explore-btn${panelOpen ? " open" : ""}`}
          onClick={() => {
            togglePanel();
            onNavigate?.();
          }}
          aria-expanded={panelOpen}
          aria-haspopup="dialog"
          aria-label={`Field notebook — ${explored} of ${TOTAL_AREAS} sections explored, ${points} points`}
          title="Field notebook — everything you have explored"
        >
          <ProgressRing value={explored / TOTAL_AREAS} size={30} />
          <span className="explore-copy">
            <strong>Field notebook</strong>
            <small>
              {explored}/{TOTAL_AREAS} sections · {points} pts
            </small>
          </span>
          <span className="explore-chev" aria-hidden="true">
            ↗
          </span>
        </button>
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
      </div>
    </motion.aside>
  );
}
