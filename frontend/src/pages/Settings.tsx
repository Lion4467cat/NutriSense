import { useState } from "react";
import { useMenu } from "../context/menu";
import { THEME_OPTS } from "../hooks/useTheme";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { Card, StatusMark } from "../ui/primitives";
import { apiBase } from "../services/api";

export default function SettingsPage() {
  const { prefs, setPrefs } = usePrefs();
  const { menu, apiUp, health, checkHealth } = useMenu();
  const { records, clearRecords } = useRecords();
  const [confirmClear, setConfirmClear] = useState(false);

  const exportData = () => {
    const blob = new Blob([JSON.stringify(records, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nutrisense-history-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-sub">Appearance, API status and local preferences.</p>
        </div>
      </div>

      <div className="settings-stack">
        <Card title="Profile">
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Display name</div>
              <div className="si-desc">
                Shown in your dashboard greeting and profile menu.
              </div>
            </div>
            <input
              className="input"
              style={{ width: 220 }}
              type="text"
              maxLength={40}
              placeholder="e.g. Priya Sharma"
              value={prefs.userName}
              onChange={(e) => setPrefs({ userName: e.target.value })}
            />
          </div>
        </Card>

        <Card title="Appearance">
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Theme</div>
              <div className="si-desc">
                Seven curated looks — each with its own coordinated accent
                colors. System follows your OS preference.
              </div>
            </div>
            <div className="theme-grid" role="radiogroup" aria-label="Theme">
              {THEME_OPTS.map((t) => (
                <button
                  key={t.id}
                  role="radio"
                  aria-checked={prefs.theme === t.id}
                  aria-label={t.label}
                  title={t.label}
                  className={
                    prefs.theme === t.id ? "theme-tile active" : "theme-tile"
                  }
                  onClick={() => setPrefs({ theme: t.id })}
                >
                  <span
                    className="theme-mini"
                    style={{
                      background: t.bg,
                      "--tile-accent": t.accent,
                      "--tile-fg": t.fg,
                      "--tile-c1": t.c1,
                      "--tile-c2": t.c2,
                    } as React.CSSProperties}
                    aria-hidden="true"
                  >
                    <span className="tm-bar" />
                    <span className="tm-line" style={{ width: "86%" }} />
                    <span className="tm-line" style={{ width: "70%" }} />
                    <span className="tm-chips">
                      <span className="tm-chip" />
                      <span className="tm-chip" />
                    </span>
                  </span>
                  <span className="theme-tile-name">{t.label}</span>
                </button>
              ))}
            </div>
          </div>
        </Card>

        <Card title="API">
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Connection status</div>
              <div className="si-desc">
                {apiUp === true
                  ? `Backend responding — ${health?.phase || "ok"}`
                  : apiUp === false
                    ? "Backend unreachable — analyses are disabled."
                    : "Checking connection…"}
              </div>
            </div>
            <div className="status-inline">
              <StatusMark level={apiUp ? "good" : apiUp === false ? "bad" : "idle"} />
              {apiUp ? "Connected" : apiUp === false ? "Disconnected" : "Checking"}
              <button className="btn btn-secondary btn-sm" onClick={checkHealth}>
                Recheck
              </button>
            </div>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Backend URL</div>
              <div className="si-desc">
                Configured via <span className="mono">VITE_API_BASE</span>.
              </div>
            </div>
            <span className="tag mono">{apiBase}</span>
          </div>
        </Card>

        <Card title="Local data" sub="History and student records live in this browser.">
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Analysis records</div>
              <div className="si-desc">
                {records.length} record{records.length === 1 ? "" : "s"} stored
                locally — export before clearing.
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={exportData}
                disabled={records.length === 0}
              >
                Export JSON
              </button>
              {confirmClear ? (
                <>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      clearRecords();
                      setConfirmClear(false);
                    }}
                  >
                    Confirm delete
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => setConfirmClear(false)}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => setConfirmClear(true)}
                  disabled={records.length === 0}
                >
                  Clear all
                </button>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
