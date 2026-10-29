import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { usePrefs, type Prefs } from "../context/prefs";
import { useGoals } from "../context/goals";
import { resolveGoal, type ProfilePref } from "../services/goals";
import { formatNum } from "../utils/format";

const EASE = [0.22, 1, 0.36, 1] as const;

const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.94, y: 16 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: "spring", stiffness: 340, damping: 30 },
  },
  exit: { opacity: 0, scale: 0.97, y: -8, transition: { duration: 0.15, ease: EASE } },
};

const stepVariants: Variants = {
  enter: (dir: number) => ({ opacity: 0, x: dir > 0 ? 24 : -24 }),
  center: { opacity: 1, x: 0, transition: { duration: 0.25, ease: EASE } },
  exit: (dir: number) => ({
    opacity: 0,
    x: dir > 0 ? -24 : 24,
    transition: { duration: 0.15, ease: EASE },
  }),
};

const STEPS = ["welcome", "profile", "goals", "done"] as const;
type Step = (typeof STEPS)[number];

const STEP_TITLE: Record<Step, string> = {
  welcome: "Welcome",
  profile: "Your profile",
  goals: "Daily goal",
  done: "Ready",
};

function sexLabel(sex: string): string {
  if (!sex) return "—";
  return sex.charAt(0).toUpperCase() + sex.slice(1);
}

function FlameIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3c3.5 4 6 6.6 6 10a6 6 0 1 1-12 0c0-2.1 1-3.7 2.5-5.3.4 1.6 1.3 2.6 2.4 3 .3-2.8.4-5.2 1.1-7.7Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ProteinIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M8.5 13.5c2.5 1.4 4.5 1.4 7 0M9.5 9.5h.01M14.5 9.5h.01"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function OnboardingModal({ onClose }: { onClose: () => void }) {
  const { prefs, setPrefs } = usePrefs();
  const { goals } = useGoals();

  const [step, setStep] = useState<Step>("welcome");
  const [dir, setDir] = useState(1);
  const dialogRef = useRef<HTMLDivElement>(null);

  const [name, setName] = useState(prefs.userName || "");
  const [sex, setSex] = useState(prefs.profile?.sex || goals?.sexes[0] || "male");
  const [ageBand, setAgeBand] = useState(
    prefs.profile?.ageBand || goals?.age_bands[0] || ""
  );
  const [activityLevel, setActivityLevel] = useState(
    prefs.profile?.activityLevel || goals?.activity_levels[0] || ""
  );
  const [customKcal, setCustomKcal] = useState(
    prefs.goalOverride ? String(prefs.goalOverride.kcal) : ""
  );
  const [customProtein, setCustomProtein] = useState(
    prefs.goalOverride ? String(prefs.goalOverride.proteinG) : ""
  );
  const [useCustomGoal, setUseCustomGoal] = useState(prefs.goalOverride != null);

  // /goals resolves after first paint, so the pickers' draft values start
  // empty. Adopt the served vocabulary once it lands, or the selects would
  // display a row the form does not actually hold (Continue stays disabled).
  useEffect(() => {
    if (!goals) return;
    setSex((s) => s || goals.sexes[0] || "male");
    setAgeBand((b) => b || goals.age_bands[0] || "");
    setActivityLevel((l) => l || goals.activity_levels[0] || "");
  }, [goals]);

  // A profile is only storable when the WHO lookup has every key: a partial
  // profile would resolve to "no goal", which is worse than the default row.
  const profileComplete = Boolean(ageBand && sex && activityLevel);
  const stepIdx = STEPS.indexOf(step);

  const go = useCallback(
    (delta: 1 | -1) => {
      setDir(delta);
      setStep(STEPS[Math.min(Math.max(stepIdx + delta, 0), STEPS.length - 1)]);
    },
    [stepIdx]
  );

  const persist = useCallback(
    (extra: Partial<Prefs> = {}) => {
      const profile: ProfilePref = { ageBand, sex, activityLevel };
      const patch: Partial<Prefs> = {
        userName: name.trim(),
        profile,
        ...extra,
      };
      const k = Number(customKcal);
      const p = Number(customProtein);
      const validOverride =
        useCustomGoal && Number.isFinite(k) && k > 0 && Number.isFinite(p) && p > 0;
      patch.goalOverride = validOverride ? { kcal: k, proteinG: p } : null;
      setPrefs(patch);
    },
    [activityLevel, ageBand, customKcal, customProtein, name, setPrefs, sex, useCustomGoal]
  );

  const finish = () => {
    persist({ setupComplete: true });
    onClose();
  };

  // Escape closes (and counts as a skip), focus starts inside the dialog.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const previewGoal = resolveGoal(
    goals,
    profileComplete ? { ageBand, sex, activityLevel } : null,
    null
  );

  return (
    <motion.div
      className="onboarding-backdrop"
      variants={backdropVariants}
      initial="hidden"
      animate="visible"
      exit="hidden"
      transition={{ duration: 0.2 }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        ref={dialogRef}
        className="onboarding-modal"
        variants={modalVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        role="dialog"
        aria-modal="true"
        aria-labelledby="onb-heading"
        tabIndex={-1}
      >
        <div className="onb-topline">
          <span className="onb-eyebrow">
            Setup · {stepIdx + 1} of {STEPS.length}
          </span>
          <div className="onb-progress" aria-hidden="true">
            {STEPS.map((s, i) => (
              <span
                key={s}
                className={`onb-dot${i === stepIdx ? " active" : i < stepIdx ? " done" : ""}`}
              />
            ))}
          </div>
          <button
            type="button"
            className="onb-close"
            onClick={onClose}
            aria-label="Close setup"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path
                d="M3 3l8 8M11 3l-8 8"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="onb-content">
          <AnimatePresence mode="wait" custom={dir}>
            <motion.div
              key={step}
              className="onb-step"
              custom={dir}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
            >
              {step === "welcome" && (
                <>
                  <div className="onb-hero-icon" aria-hidden="true">
                    <svg width="44" height="44" viewBox="0 0 48 48" fill="none">
                      <circle cx="24" cy="24" r="21" fill="var(--accent-soft)" />
                      <path
                        d="M24 12v24M12 24h24"
                        stroke="var(--accent)"
                        strokeWidth="0"
                      />
                      <ellipse cx="24" cy="26" rx="12" ry="9" stroke="var(--accent)" strokeWidth="2" />
                      <path d="M16 22c3-4 5-4 8-1s5 3 8-1" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
                      <circle cx="20" cy="28" r="1.6" fill="var(--accent)" />
                      <circle cx="28" cy="29" r="1.2" fill="var(--accent)" />
                    </svg>
                  </div>
                  <h2 className="onb-title" id="onb-heading">
                    Set up your profile
                  </h2>
                  <p className="onb-desc">
                    Your name, sex, age band and activity level turn WHO guidance
                    into your own daily energy and protein targets — then every
                    meal you capture is shown as a share of that goal.
                  </p>
                  <ul className="onb-points">
                    <li>Takes about 30 seconds</li>
                    <li>Stored in this browser only</li>
                    <li>Editable any time in Settings</li>
                  </ul>
                </>
              )}

              {step === "profile" && (
                <>
                  <h2 className="onb-title" id="onb-heading">
                    Your profile
                  </h2>
                  <p className="onb-desc">
                    WHO goal tables are keyed by age band, sex and activity
                    level — these three fields pick your row.
                  </p>
                  <div className="onb-form">
                    <label className="onb-label">
                      <span className="onb-label-text">Display name</span>
                      <input
                        className="onb-input"
                        type="text"
                        maxLength={40}
                        placeholder="e.g. Priya Sharma"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        autoFocus
                        autoComplete="name"
                      />
                    </label>

                    <div className="onb-label">
                      <span className="onb-label-text" id="onb-sex-label">
                        Sex
                      </span>
                      <div
                        className="onb-radio-group"
                        role="radiogroup"
                        aria-labelledby="onb-sex-label"
                      >
                        {(goals?.sexes ?? ["male", "female"]).map((s) => (
                          <button
                            key={s}
                            type="button"
                            role="radio"
                            aria-checked={sex === s}
                            className={`onb-radio-btn${sex === s ? " active" : ""}`}
                            onClick={() => setSex(s)}
                          >
                            {sexLabel(s)}
                          </button>
                        ))}
                      </div>
                    </div>

                    <label className="onb-label">
                      <span className="onb-label-text">Age band</span>
                      <select
                        className="onb-select"
                        value={ageBand}
                        onChange={(e) => setAgeBand(e.target.value)}
                      >
                        {(goals?.age_bands ?? []).map((b) => (
                          <option key={b} value={b}>
                            {b} years
                          </option>
                        ))}
                        {!goals && <option value="">Loading…</option>}
                      </select>
                    </label>

                    <label className="onb-label">
                      <span className="onb-label-text">Activity level</span>
                      <select
                        className="onb-select"
                        value={activityLevel}
                        onChange={(e) => setActivityLevel(e.target.value)}
                      >
                        {(goals?.activity_levels ?? []).map((l) => (
                          <option key={l} value={l}>
                            {sexLabel(l)}
                          </option>
                        ))}
                        {!goals && <option value="">Loading…</option>}
                      </select>
                    </label>

                    {!goals && (
                      <p className="field-hint" role="status">
                        Goal tables are still loading — you can keep this step's
                        defaults and edit later in Settings.
                      </p>
                    )}
                  </div>
                </>
              )}

              {step === "goals" && (
                <>
                  <h2 className="onb-title" id="onb-heading">
                    Daily goal
                  </h2>
                  <p className="onb-desc">
                    {profileComplete
                      ? "These are the WHO daily targets for your profile. Keep them, or set your own."
                      : "Pick your age band, sex and activity level on the previous step to see your WHO targets."}
                  </p>

                  <div className="onb-goal-preview">
                    <div className="onb-goal-card">
                      <span className="onb-goal-icon" aria-hidden="true">
                        <FlameIcon />
                      </span>
                      <div>
                        <div className="onb-goal-value">
                          {previewGoal.kcal != null ? formatNum(previewGoal.kcal, 0) : "—"}
                        </div>
                        <div className="onb-goal-unit">kcal / day</div>
                      </div>
                    </div>
                    <div className="onb-goal-card">
                      <span className="onb-goal-icon" aria-hidden="true">
                        <ProteinIcon />
                      </span>
                      <div>
                        <div className="onb-goal-value">
                          {previewGoal.proteinG != null
                            ? formatNum(previewGoal.proteinG, 1)
                            : "—"}
                        </div>
                        <div className="onb-goal-unit">g protein / day</div>
                      </div>
                    </div>
                  </div>

                  <label className="onb-toggle">
                    <input
                      type="checkbox"
                      checked={useCustomGoal}
                      onChange={(e) => setUseCustomGoal(e.target.checked)}
                    />
                    <span>Set my own daily goal instead</span>
                  </label>

                  <AnimatePresence initial={false}>
                    {useCustomGoal && (
                      <motion.div
                        className="onb-custom-goals"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.18, ease: EASE }}
                      >
                        <label className="onb-label">
                          <span className="onb-label-text">Energy (kcal / day)</span>
                          <input
                            className="onb-input"
                            type="number"
                            inputMode="numeric"
                            min={100}
                            step={50}
                            placeholder="e.g. 2000"
                            value={customKcal}
                            onChange={(e) => setCustomKcal(e.target.value)}
                          />
                        </label>
                        <label className="onb-label">
                          <span className="onb-label-text">Protein (g / day)</span>
                          <input
                            className="onb-input"
                            type="number"
                            inputMode="numeric"
                            min={1}
                            step={1}
                            placeholder="e.g. 55"
                            value={customProtein}
                            onChange={(e) => setCustomProtein(e.target.value)}
                          />
                        </label>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              )}

              {step === "done" && (
                <>
                  <div className="onb-hero-icon onb-hero-success" aria-hidden="true">
                    <svg width="44" height="44" viewBox="0 0 48 48" fill="none">
                      <circle cx="24" cy="24" r="21" fill="var(--pass-soft)" />
                      <path
                        d="M15 24.5l6 6 12-13"
                        stroke="var(--pass)"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                  <h2 className="onb-title" id="onb-heading">
                    You're all set{name.trim() ? `, ${name.trim().split(/\s+/)[0]}` : ""}
                  </h2>
                  <p className="onb-desc">
                    Saved in this browser. You can change any of it later from
                    Settings.
                  </p>
                  <dl className="onb-summary">
                    <div>
                      <dt>Name</dt>
                      <dd>{name.trim() || "—"}</dd>
                    </div>
                    <div>
                      <dt>Sex</dt>
                      <dd>{sexLabel(sex)}</dd>
                    </div>
                    <div>
                      <dt>Age band</dt>
                      <dd>{ageBand || "—"}</dd>
                    </div>
                    <div>
                      <dt>Activity</dt>
                      <dd>{activityLevel ? sexLabel(activityLevel) : "—"}</dd>
                    </div>
                    <div>
                      <dt>Daily goal</dt>
                      <dd>
                        {useCustomGoal && customKcal && customProtein
                          ? `${customKcal} kcal · ${customProtein} g`
                          : previewGoal.kcal != null
                            ? `${formatNum(previewGoal.kcal, 0)} kcal · ${formatNum(
                                previewGoal.proteinG,
                                1
                              )} g protein`
                            : "—"}
                      </dd>
                    </div>
                  </dl>
                </>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="onb-actions">
          {stepIdx > 0 && step !== "done" && (
            <button className="btn btn-ghost" onClick={() => go(-1)} type="button">
              Back
            </button>
          )}
          {step === "welcome" && (
            <button className="btn btn-primary onb-btn-main" onClick={() => go(1)} type="button">
              Get started
            </button>
          )}
          {step === "profile" && (
            <button
              className="btn btn-primary onb-btn-main"
              onClick={() => go(1)}
              type="button"
              disabled={!profileComplete}
              title={profileComplete ? undefined : "Pick a sex, age band and activity level"}
            >
              Continue
            </button>
          )}
          {step === "goals" && (
            <button
              className="btn btn-primary onb-btn-main"
              onClick={() => {
                persist();
                go(1);
              }}
              type="button"
            >
              Save & continue
            </button>
          )}
          {step === "done" && (
            <button className="btn btn-primary onb-btn-main" onClick={finish} type="button">
              Start analyzing
            </button>
          )}
          {step !== "done" && (
            <button className="onb-skip" onClick={onClose} type="button">
              Skip for now
            </button>
          )}
        </div>

        <p className="onb-footnote">
          {STEP_TITLE[step]} · Stored locally · Not medical advice
        </p>
      </motion.div>
    </motion.div>
  );
}
