import { usePrefs, type AppMode } from "../context/prefs";

/**
 * The School ↔ General switch (ADR 0003). School keeps today's
 * verdict-centric UI; General shows grams + nutrients + share of the Daily
 * goal. Mode is frontend-only state, persisted in nutrisense.prefs.v1 —
 * /analyze is never told which mode is active.
 */
export default function ModeSwitch({ className = "" }: { className?: string }) {
  const { prefs, setPrefs } = usePrefs();
  const mode: AppMode = prefs.mode ?? "school";

  const btn = (m: AppMode, label: string) => (
    <button
      type="button"
      className={mode === m ? "active" : ""}
      aria-pressed={mode === m}
      onClick={() => setPrefs({ mode: m })}
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
