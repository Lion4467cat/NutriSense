import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useMenu } from "../context/menu";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { attention as selectAttention } from "../services/records";
import { VerdictPill } from  "../result/VerdictPill";
import { formatDate } from  "../utils/format";
import {
  IconBell,
  IconHelp,
  IconMenu,
  IconMonitor,
  IconMoon,
  IconSearch,
  IconSun,
} from  "../ui/Icon";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/analyze": "Analyze Meal",
  "/history": "Analysis History",
  "/students": "Student Records",
  "/menu": "Menu & Standards",
  "/analytics": "Analytics",
  "/settings": "Settings",
  "/result": "Analysis Result",
};

function titleFor(pathname: string): string {
  if (pathname.startsWith("/result")) return TITLES["/result"];
  if (pathname.startsWith("/students/")) return "Student Detail";
  return TITLES[pathname] || "NutriSense";
}

export default function Topbar({
  onOpenDrawer,
  onToggleTheme,
}: {
  onOpenDrawer: () => void;
  onToggleTheme: () => void;
}) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { apiUp } = useMenu();
  const { prefs, setPrefs } = usePrefs();
  const { records } = useRecords();
  const [search, setSearch] = useState(params.get("q") || "");
  const [profileOpen, setProfileOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const alertsRef = useRef<HTMLDivElement>(null);

  const attention = useMemo(
    () => selectAttention(records).slice(0, 6),
    [records]
  );

  useEffect(() => {
    setSearch(params.get("q") || "");
  }, [params]);

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

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(search.trim() ? `/history?q=${encodeURIComponent(search.trim())}` : "/history");
  };

  const resolved =
    prefs.theme !== "system"
      ? prefs.theme
      : window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
  const darkish =
    resolved === "dark" || resolved === "midnight" || resolved === "oled";

  const crumbRoot =
    pathname === "/" ? "Workspace" : pathname.startsWith("/result")
      ? "Workspace / History"
      : "Workspace";

  return (
    <header className="topbar">
      <button
        className="icon-btn hamburger"
        onClick={onOpenDrawer}
        aria-label="Open navigation menu"
      >
        <IconMenu size={18} />
      </button>

      <div className="crumb">
        <span className="crumb-root">{crumbRoot}</span>
        <span className="crumb-sep" aria-hidden="true">
          /
        </span>
        <span className="crumb-page">{titleFor(pathname)}</span>
      </div>

      <div className="topbar-spacer" />

      <form className="search-box" onSubmit={submitSearch} role="search">
        <IconSearch size={14} />
        <input
          type="search"
          placeholder="Search analyses…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search analyses"
        />
      </form>

      <div ref={alertsRef} style={{ position: "relative" }}>
        <button
          className="icon-btn"
          onClick={() => setAlertsOpen((o) => !o)}
          aria-label={
            attention.length
              ? `Notifications: ${attention.length} need attention`
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
                Local analyses needing attention
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
                <VerdictPill verdict={r.summary.verdict} />
              </button>
            ))}
            {attention.length === 0 && apiUp !== false && (
              <div className="pop-empty">Nothing needs attention.</div>
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

      <button
        className="icon-btn"
        onClick={onToggleTheme}
        aria-label={`Switch to ${resolved === "dark" ? "light" : "dark"} mode`}
        title="Toggle theme"
      >
        {darkish ? <IconSun size={17} /> : <IconMoon size={17} />}
      </button>

      <div ref={profileRef} style={{ position: "relative" }}>
        <button
          className="profile-btn"
          onClick={() => setProfileOpen((o) => !o)}
          aria-expanded={profileOpen}
          aria-haspopup="menu"
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
            {prefs.userName.trim().split(/\s+/)[0] || "Monitor"}
          </span>
        </button>
        {profileOpen && (
          <div className="menu-pop" role="menu">
            <div className="pop-head">
              <div className="workspace-name">NutriSense Monitor</div>
              <div className="workspace-role">
                {apiUp ? "Backend connected" : "Backend offline"} · local workspace
              </div>
            </div>
            <button
              className="pop-item"
              role="menuitem"
              onClick={() => {
                setProfileOpen(false);
                navigate("/settings");
              }}
            >
              <IconHelp size={15} /> Help & settings
            </button>
            <button
              className="pop-item"
              role="menuitem"
              onClick={() => {
                setProfileOpen(false);
                setPrefs({ theme: darkish ? "light" : "dark" });
              }}
            >
              <IconMonitor size={15} /> Theme: {prefs.theme}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
