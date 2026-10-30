import type { GoalsResponse } from "../types/api";

/**
 * General-mode Daily goal resolution (spec 002, ADR 0003): goal VALUES come
 * from the backend (GET /goals, WHO tables); the MATH lives here in the
 * frontend, computed from records already stored — goal edits never
 * re-analyze. Pure functions, vitest-tested like the records selectors.
 */

/** One-time General-mode profile (WHO goal lookup keys, spec 002 T-D). */
export interface ProfilePref {
  ageBand: string;
  sex: string;
  activityLevel: string;
}

/** User-entered Daily goal override; null = use the served WHO default. */
export interface GoalOverridePref {
  kcal: number;
  proteinG: number;
}

export interface DailyGoal {
  kcal: number | null;
  proteinG: number | null;
  /** where the numbers came from: the served WHO table or the user's entry */
  source: "who" | "custom" | "none";
  /** true when the profile itself is still the first-served default */
  defaulted: boolean;
  /** the profile the WHO lookup used (null for custom/none) */
  profile: ProfilePref | null;
}

/** First-served values of each picker — the labelled fallback profile. */
export function defaultProfile(goals: GoalsResponse | null): ProfilePref | null {
  if (!goals) return null;
  return {
    ageBand: goals.age_bands[0] ?? "",
    sex: goals.sexes[0] ?? "",
    activityLevel: goals.activity_levels[0] ?? "",
  };
}

function servedGoal(
  goals: GoalsResponse,
  profile: ProfilePref
): { kcal: number | null; proteinG: number | null } {
  const band = goals.daily[profile.ageBand];
  const row =
    band?.[profile.sex as "male" | "female"] ??
    band?.male ??
    band?.female ??
    undefined;
  if (!row) return { kcal: null, proteinG: null };
  const kcal = row.energy_kcal?.[profile.activityLevel];
  return {
    kcal: typeof kcal === "number" && Number.isFinite(kcal) ? kcal : null,
    proteinG:
      typeof row.protein_g === "number" && Number.isFinite(row.protein_g)
        ? row.protein_g
        : null,
  };
}

/**
 * The goal the UI should display: the user's override when present, else the
 * served WHO value for the stored profile, else the first-served default
 * profile (marked `defaulted` so the UI can label it honestly). Any gap in
 * the WHO table resolves to null shares — never an invented number.
 */
export function resolveGoal(
  goals: GoalsResponse | null,
  profile: ProfilePref | null,
  override: GoalOverridePref | null
): DailyGoal {
  if (
    override &&
    Number.isFinite(override.kcal) &&
    override.kcal > 0 &&
    Number.isFinite(override.proteinG) &&
    override.proteinG > 0
  ) {
    return {
      kcal: override.kcal,
      proteinG: override.proteinG,
      source: "custom",
      defaulted: false,
      profile: null,
    };
  }
  if (!goals) return { kcal: null, proteinG: null, source: "none", defaulted: false, profile: null };
  const effective = profile ?? defaultProfile(goals);
  if (!effective?.ageBand || !effective.sex || !effective.activityLevel) {
    return { kcal: null, proteinG: null, source: "none", defaulted: false, profile: effective };
  }
  const { kcal, proteinG } = servedGoal(goals, effective);
  return {
    kcal,
    proteinG,
    source: "who",
    defaulted: profile === null,
    profile: effective,
  };
}

/** Meal mean → share of the Daily goal; null whenever either side is missing. */
export function shareOfGoal(
  value: number | null | undefined,
  goal: number | null | undefined
): number | null {
  if (
    value == null ||
    goal == null ||
    !Number.isFinite(value) ||
    !Number.isFinite(goal) ||
    goal <= 0
  ) {
    return null;
  }
  return value / goal;
}
