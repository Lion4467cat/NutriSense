import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { EASE } from "../ui/motion";
import { useMenu } from "../context/menu";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { useExplore } from "../context/explore";
import { TOTAL_AREAS, exploredCount } from "../explore/achievements";
import { ProgressRing } from "../ui/fx";
import {
  attention as selectAttention,
  unmeasured as selectUnmeasured,
} from "../services/records";
import { VerdictPill } from  "../result/VerdictPill";
import ModeSwitch from "../ui/ModeSwitch";
import { formatDate } from  "../utils/format";
import {
  IconBell,
  IconMenu,
  IconMoon,
  IconSun,
  IconX,
  IconSettings,
} from  "../ui/Icon";

export default function Topbar({
  drawerOpen,
  onToggleDrawer,
}: {
  drawerOpen: boolean;
  onToggleDrawer: () => void;
}) {
  const navigate = useNavigate();
  const { apiUp } = useMenu();
  const { prefs, setPrefs } = usePrefs();
  const { records } = useRecords();
  const { state: explored, panelOpen, togglePanel } = useExplore();
  const areasSeen = exploredCount(explored);
  const general = (prefs.mode ?? "school") === "general";
  const darkTheme =
    ["dark", "nord", "rosepine", "dracula", "catppuccin"].includes(prefs.theme) ||
    (prefs.theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  const [profileOpen, setProfileOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const alertsRef = useRef<HTMLDivElement>(null);

  // School: verdicts needing attention. General: analyses without numbers.
  const attention = useMemo(
    () =>
      general
        ? selectUnmeasured(records).slice(0, 6)
        : selectAttention(records).slice(0, 6),
    [records, general]
  );

  useEffect(() => {
    if (!profileOpen && !alertsOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (alertsRef.current && !alertsRef.current.contains(e.target as Node)) {
        setAlertsOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [profileOpen, alertsOpen]);

  return (
    <motion.header
      className="topbar"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE }}
    >
      <button
        className="icon-btn hamburger"
        onClick={onToggleDrawer}
        aria-label={drawerOpen ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={drawerOpen}
      >
        {drawerOpen ? <IconX size={18} /> : <IconMenu size={18} />}
      </button>

      <div className="topbar-spacer" />

      <button
        className="icon-btn theme-toggle"
        onClick={() => setPrefs({ theme: darkTheme ? "light" : "dark" })}
        aria-label={darkTheme ? "Switch to light theme" : "Switch to dark theme"}
        title={darkTheme ? "Switch to light theme" : "Switch to dark theme"}
      >
        <motion.span
          key={darkTheme ? "sun" : "moon"}
          initial={{ rotate: -80, opacity: 0, scale: 0.6 }}
          animate={{ rotate: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, ease: EASE }}
          style={{ display: "grid", placeItems: "center" }}
        >
          {darkTheme ? <IconSun size={17} /> : <IconMoon size={17} />}
        </motion.span>
      </button>

      <ModeSwitch className="topbar-mode" />

      <button
        className="icon-btn explorer-btn"
        onClick={togglePanel}
        aria-expanded={panelOpen}
        aria-haspopup="dialog"
        aria-label={`Field notebook — ${areasSeen} of ${TOTAL_AREAS} sections explored`}
        title="Field notebook"
      >
        <ProgressRing value={areasSeen / TOTAL_AREAS} size={18} stroke={2} />
        {areasSeen > 0 && areasSeen < TOTAL_AREAS && (
          <span className="explore-dot" aria-hidden="true" />
        )}
      </button>

      <div ref={alertsRef} style={{ position: "relative" }}>
        <button
          className="icon-btn"
          onClick={() => setAlertsOpen((o) => !o)}
          aria-label={
            attention.length
              ? general
                ? `Notifications: ${attention.length} analyses have no nutrition numbers`
                : `Notifications: ${attention.length} need attention`
              : "Notifications"
          }
          aria-expanded={alertsOpen}
          aria-haspopup="menu"
          title="Notifications"
        >
          <IconBell size={17} />
          {apiUp === false ? (
            <span className="alert-dot" aria-hidden="true" />
          ) : (
            attention.length > 0 && (
              <span className="count-badge" aria-hidden="true">
                {attention.length}
              </span>
            )
          )}
        </button>
        {alertsOpen && (
          <div className="menu-pop notif-pop" role="menu">
            <div className="pop-head">
              <div className="workspace-name">Notifications</div>
              <div className="workspace-role">
                {general
                  ? "Local analyses without nutrition numbers"
                  : "Local analyses needing attention"}
              </div>
            </div>
            {apiUp === false && (
              <button
                className="pop-item pop-warn"
                role="menuitem"
                onClick={() => {
                  setAlertsOpen(false);
                  navigate("/settings");
                }}
              >
                Backend unreachable — open settings
              </button>
            )}
            {attention.map((r) => (
              <button
                key={r.id}
                className="pop-item"
                role="menuitem"
                onClick={() => {
                  setAlertsOpen(false);
                  navigate(`/result/${r.id}`);
                }}
              >
                <span className="pop-item-body">
                  <span className="pop-item-title">
                    {r.summary.dish || "Unrecognized dish"}
                  </span>
                  <span className="pop-item-sub">
                    {formatDate(r.createdAt)}
                    {r.student?.name ? ` · ${r.student.name}` : ""}
                  </span>
                </span>
                {general ? (
                  <span className="tag">no numbers</span>
                ) : (
                  <VerdictPill verdict={r.summary.verdict} />
                )}
              </button>
            ))}
            {attention.length === 0 && apiUp !== false && (
              <div className="pop-empty">
                {general ? "Every analysis has numbers." : "Nothing needs attention."}
              </div>
            )}
            <button
              className="pop-item pop-foot"
              role="menuitem"
              onClick={() => {
                setAlertsOpen(false);
                navigate("/history");
              }}
            >
              View all in history →
            </button>
          </div>
        )}
      </div>

      <div ref={profileRef} style={{ position: "relative" }}>
        <button
          className="profile-btn"
          onClick={() => setProfileOpen((o) => !o)}
          aria-expanded={profileOpen}
          aria-haspopup="menu"
          aria-label="Open profile menu"
        >
          <span className="avatar" aria-hidden="true">
            {(() => {
              const n = prefs.userName.trim();
              if (!n) return "NM";
              const parts = n.split(/\s+/);
              return (
                parts[0][0].toUpperCase() +
                (parts[1]?.[0]?.toUpperCase() ?? parts[0][1]?.toUpperCase() ?? "")
              );
            })()}
          </span>
          <span className="profile-name">
              {prefs.userName.trim().split(/\s+/)[0] || "Workspace"}
          </span>
        </button>
        {profileOpen && (
          <div className="menu-pop" role="menu">
            <div className="pop-head">
              <div className="workspace-name">Your workspace</div>
              <div className="workspace-role">Settings and meal preferences</div>
            </div>
            <button
              className="pop-item"
              role="menuitem"
              onClick={() => {
                setProfileOpen(false);
                navigate("/settings");
              }}
            >
              <IconSettings size={15} /> Settings
            </button>
          </div>
        )}
      </div>
    </motion.header>
  );
}
