import { useState } from "react";
import { useGoals } from "../context/goals";
import { useMenu } from "../context/menu";
import { THEME_OPTS } from "../hooks/useTheme";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { useOnboarding } from "../context/onboarding";
import { Card, StatusMark } from "../ui/primitives";
import ModeSwitch from "../ui/ModeSwitch";
import { apiBase } from "../services/api";
import { defaultProfile, resolveGoal, type ProfilePref } from "../services/goals";
import { formatNum } from "../utils/format";

export default function SettingsPage() {
  const { prefs, setPrefs } = usePrefs();
  const { menu, apiUp, health, checkHealth } = useMenu();
  const { goals, goalsError, reloadGoals } = useGoals();
  const { records, clearRecords } = useRecords();
  const { openWizard } = useOnboarding();
  const [confirmClear, setConfirmClear] = useState(false);

  const goal = resolveGoal(goals, prefs.profile, prefs.goalOverride);
  const served = defaultProfile(goals);
  const profile = prefs.profile ?? served;
  const setProfileField = (patch: Partial<ProfilePref>) => {
    if (!profile) return;
    setPrefs({
      profile: {
        ageBand: profile.ageBand || "",
        sex: profile.sex || "",
        activityLevel: profile.activityLevel || "",
        ...patch,
      },
      // editing the profile by hand counts as having entered the details
      setupComplete: true,
    });
  };

  // User-entered goal override: edited in a small draft form, stored only
  // when both values are positive — clearing reverts to the WHO default.
  const [goalDraft, setGoalDraft] = useState<{ kcal: string; proteinG: string } | null>(
    null
  );
  const saveGoal = () => {
    if (!goalDraft) return;
    const k = Number(goalDraft.kcal);
    const p = Number(goalDraft.proteinG);
    if (Number.isFinite(k) && k > 0 && Number.isFinite(p) && p > 0) {
      setPrefs({ goalOverride: { kcal: k, proteinG: p } });
    }
    setGoalDraft(null);
  };

  const goalSourceLabel =
    goal.source === "custom"
      ? "your own goal"
      : goal.source === "who"
        ? goal.defaulted
          ? "WHO default (first-served profile)"
          : "WHO default for your profile"
        : "no goal available";

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
          <p className="page-sub">Appearance, app mode, Daily goal and local preferences.</p>
        </div>
      </div>

      <div className="settings-stack">
        <Card
          title="App mode"
          sub="School keeps the compliance verdicts; General shows grams, nutrients and share of your Daily goal."
        >
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">
                Mode: {prefs.mode === "general" ? "General" : "School"}
              </div>
              <div className="si-desc">
                {prefs.mode === "general"
                  ? "General mode — every recognized dish gets grams + nutrients as a share of your Daily goal. No verdicts, no school capture fields."
                  : "School mode — PM POSHAN compliance for menu dishes, judged under Policy, exactly as before."}
              </div>
            </div>
            <ModeSwitch />
          </div>
        </Card>

        <Card
          title="Your profile"
          sub="Name, sex, age band and activity level feed the WHO Daily goal lookup; your own goal always wins."
          action={
            <button className="btn btn-secondary btn-sm" onClick={openWizard}>
              Open setup guide
            </button>
          }
        >
          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Display name</div>
              <div className="si-desc">Shown in the dashboard greeting.</div>
            </div>
            <input
              className="input"
              style={{ width: 220 }}
              type="text"
              maxLength={40}
              placeholder="e.g. Priya Sharma"
              aria-label="Display name"
              value={prefs.userName}
              onChange={(e) => setPrefs({ userName: e.target.value })}
            />
          </div>

          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Profile</div>
              <div className="si-desc">
                {profile == null
                  ? "Goal data has not loaded yet — start the backend and retry."
                  : prefs.profile == null
                    ? "Showing served defaults — pick your own age band, sex and activity level to personalize."
                    : "Used to look up the WHO Daily goal tables."}
              </div>
            </div>
            <div className="profile-pickers">
              <label className="field">
                <span className="field-label">Age band</span>
                <select
                  className="select"
                  value={profile?.ageBand ?? ""}
                  onChange={(e) => setProfileField({ ageBand: e.target.value })}
                  disabled={!goals}
                >
                  {!goals && <option value="">—</option>}
                  {goals?.age_bands.map((b) => (
                    <option key={b} value={b}>
                      {b} years
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Sex</span>
                <select
                  className="select"
                  value={profile?.sex ?? ""}
                  onChange={(e) => setProfileField({ sex: e.target.value })}
                  disabled={!goals}
                >
                  {!goals && <option value="">—</option>}
                  {goals?.sexes.map((s) => (
                    <option key={s} value={s}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field-label">Activity</span>
                <select
                  className="select"
                  value={profile?.activityLevel ?? ""}
                  onChange={(e) => setProfileField({ activityLevel: e.target.value })}
                  disabled={!goals}
                >
                  {!goals && <option value="">—</option>}
                  {goals?.activity_levels.map((l) => (
                    <option key={l} value={l}>
                      {l.charAt(0).toUpperCase() + l.slice(1)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="setting-row">
            <div className="setting-info">
              <div className="si-title">Daily goal</div>
              <div className="si-desc">
                {goal.kcal == null
                  ? "No goal available — set your profile above."
                  : `${formatNum(goal.kcal, 0)} kcal · ${formatNum(goal.proteinG, 1)} g protein — ${goalSourceLabel}.`}
              </div>
            </div>
            {goalDraft ? (
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  className="input"
                  style={{ width: 110 }}
                  type="number"
                  min={1}
                  placeholder="kcal/day"
                  aria-label="Daily energy goal in kcal"
                  value={goalDraft.kcal}
                  onChange={(e) => setGoalDraft({ ...goalDraft, kcal: e.target.value })}
                />
                <input
                  className="input"
                  style={{ width: 110 }}
                  type="number"
                  min={1}
                  step="0.1"
                  placeholder="g protein/day"
                  aria-label="Daily protein goal in grams"
                  value={goalDraft.proteinG}
                  onChange={(e) => setGoalDraft({ ...goalDraft, proteinG: e.target.value })}
                />
                <button className="btn btn-primary btn-sm" onClick={saveGoal}>
                  Save
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => setGoalDraft(null)}>
                  Cancel
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    setGoalDraft({
                      kcal: String(prefs.goalOverride?.kcal ?? goal.kcal ?? ""),
                      proteinG: String(prefs.goalOverride?.proteinG ?? goal.proteinG ?? ""),
                    })
                  }
                >
                  Enter my own goal
                </button>
                {prefs.goalOverride && (
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => setPrefs({ goalOverride: null })}
                  >
                    Reset to WHO default
                  </button>
                )}
              </div>
            )}
          </div>

          {(goalsError || !goals) && (
            <div className="banner warn" style={{ marginTop: 10 }}>
              <span aria-hidden="true">!</span>
              <div>
                <strong>Goal values could not be loaded</strong>
                The WHO goal table comes from the backend (GET /goals). Retry
                once the API is running.
                <button className="btn btn-secondary btn-sm" style={{ marginTop: 8 }} onClick={reloadGoals}>
                  Retry
                </button>
              </div>
            </div>
          )}

          {goals && (
            <div style={{ marginTop: 12 }}>
              {goals.caveats.map((c, i) => (
                <p className="field-hint" key={i} style={{ marginBottom: 4 }}>
                  {c}
                </p>
              ))}
              <p className="field-hint">
                Sources: {goals.source.s1} · {goals.source.s2} (verified{" "}
                {goals.source.verified}).
              </p>
            </div>
          )}
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
