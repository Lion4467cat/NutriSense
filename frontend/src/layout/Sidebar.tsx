import { useEffect, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { introItem, introStagger } from "../ui/motion";
import { ProgressRing } from "../ui/fx";
import { useMenu } from "../context/menu";
import { useRecords } from "../context/records";
import { useExplore } from "../context/explore";
import { TOTAL_AREAS, exploredCount, pointsFor } from "../explore/achievements";
import { apiBase } from  "../services/api";
import {
  IconBook,
  IconCamera,
  IconChart,
  IconChevronDown,
  IconDashboard,
  IconHistory,
  IconSettings,
  IconSparkle,
  IconUsers,
  LogoMark,
} from  "../ui/Icon";

const PRIMARY_NAV = [
  { to: "/", label: "Home", icon: IconDashboard, end: true },
  { to: "/analyze", label: "Analyze", icon: IconCamera },
  { to: "/history", label: "History", icon: IconHistory },
  { to: "/analytics", label: "Insights", icon: IconChart },
];

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

  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setMoreOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMoreOpen(false);
    }
    if (moreOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
        document.removeEventListener("keydown", handleKeyDown);
      };
    }
  }, [moreOpen]);

  const isMoreActive =
    pathname.startsWith("/students") ||
    pathname.startsWith("/menu") ||
    pathname.startsWith("/settings");

  const isActive = (to: string, end?: boolean) =>
    end ? pathname === to : pathname.startsWith(to);
  const statusLabel =
    apiUp === true ? "API connected" : apiUp === false ? "API unreachable" : "Connecting…";

  return (
    <motion.aside
      className="sidebar"
      aria-label="Primary"
      variants={introStagger}
      initial="hidden"
      animate="show"
    >
      <motion.div variants={introItem}>
        <button
          type="button"
          className="sidebar-brand brand-link"
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
      </motion.div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {PRIMARY_NAV.map(({ to, label, icon: Icon, end }) => (
          <motion.div
            key={to}
            variants={introItem}
            whileTap={{ scale: 0.95 }}
            style={{ display: "flex", flexShrink: 0 }}
          >
            <NavLink
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
            </NavLink>
          </motion.div>
        ))}

        {/* Desktop More dropdown / Mobile drawer section */}
        <div className="sidebar-more" ref={moreRef}>
          <button
            className={`nav-link sidebar-more-button${isMoreActive ? " active" : ""}`}
            type="button"
            aria-expanded={moreOpen}
            aria-haspopup="menu"
            onClick={() => setMoreOpen((open) => !open)}
            title="School tools, settings, and more"
          >
            <span>More</span>
            <IconChevronDown size={14} className={moreOpen ? "rotate-180" : ""} />
          </button>

          <AnimatePresence>
            {moreOpen && (
              <motion.div
                className="sidebar-more-menu"
                role="menu"
                aria-label="More sections"
                initial={{ opacity: 0, y: -4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4, scale: 0.98 }}
                transition={{ duration: 0.15 }}
              >
                <NavLink
                  to="/students"
                  role="menuitem"
                  className={({ isActive }) => `more-link${isActive ? " active" : ""}`}
                  onClick={() => {
                    setMoreOpen(false);
                    onNavigate?.();
                  }}
                >
                  <IconUsers size={16} />
                  <span>Student records</span>
                </NavLink>

                <NavLink
                  to="/menu"
                  role="menuitem"
                  className={({ isActive }) => `more-link${isActive ? " active" : ""}`}
                  onClick={() => {
                    setMoreOpen(false);
                    onNavigate?.();
                  }}
                >
                  <IconBook size={16} />
                  <span>Menu & standards</span>
                  {menu && Object.keys(menu.dishes).length > 0 && (
                    <span className="nav-badge num" style={{ marginLeft: "auto" }}>
                      {Object.keys(menu.dishes).length}
                    </span>
                  )}
                </NavLink>

                <NavLink
                  to="/settings"
                  role="menuitem"
                  className={({ isActive }) => `more-link${isActive ? " active" : ""}`}
                  onClick={() => {
                    setMoreOpen(false);
                    onNavigate?.();
                  }}
                >
                  <IconSettings size={16} />
                  <span>Settings & preferences</span>
                </NavLink>

                <button
                  type="button"
                  role="menuitem"
                  className="more-link explorer-more-btn"
                  onClick={() => {
                    setMoreOpen(false);
                    togglePanel();
                    onNavigate?.();
                  }}
                  style={{
                    background: "none",
                    border: 0,
                    width: "100%",
                    textAlign: "left",
                    cursor: "pointer",
                    font: "inherit",
                  }}
                >
                  <IconSparkle size={16} />
                  <span>Field notebook & Explorer</span>
                  <span className="nav-badge num" style={{ marginLeft: "auto" }}>
                    {explored}/{TOTAL_AREAS}
                  </span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </nav>

      <div className="sidebar-foot">
        <button
          type="button"
          className={`explore-btn${panelOpen ? " open" : ""}`}
          onClick={togglePanel}
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
