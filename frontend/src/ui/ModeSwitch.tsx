import { usePrefs, type AppMode } from "../context/prefs";
import { useOnboarding } from "../context/onboarding";

/**
 * The School ↔ General switch (ADR 0003). School keeps today's
 * verdict-centric UI; General shows grams + nutrients + share of the Daily
 * goal. Mode is frontend-only state, persisted in nutrisense.prefs.v1 —
 * /analyze is never told which mode is active.
 *
 * Profile details (name, sex, age band, activity level) exist only to pick a
 * WHO Daily goal row, so General is the one mode that needs them. Every
 * switch into General without a saved profile asks — no persistent banner,
 * no nagging in School.
 */
export default function ModeSwitch({ className = "" }: { className?: string }) {
  const { prefs, setPrefs } = usePrefs();
  const { openWizard } = useOnboarding();
  const mode: AppMode = prefs.mode ?? "school";

  const hasProfile = Boolean(
    prefs.profile?.ageBand && prefs.profile?.sex && prefs.profile?.activityLevel
  );

  const choose = (m: AppMode) => {
    setPrefs({ mode: m });
    if (m === "general" && !hasProfile) openWizard();
  };

  const btn = (m: AppMode, label: string) => (
    <button
      type="button"
      className={mode === m ? "active" : ""}
      aria-pressed={mode === m}
      onClick={() => choose(m)}
    >
      {label}
    </button>
  );

  return (
    <div className={`seg mode-switch${className ? ` ${className}` : ""}`} role="group" aria-label="App mode">
      {btn("school", "School")}
      {btn("general", "General")}
    </div>
  );
}
