import { describe, expect, it } from "vitest";
import type { GoalsResponse } from "../types/api";
import { defaultProfile, resolveGoal, shareOfGoal } from "./goals";

/** Mirrors the GET /goals wire (main.goals()) on a small slice of the table. */
const GOALS: GoalsResponse = {
  age_bands: ["5-8", "9-11", "18-29", "60-plus"],
  sexes: ["male", "female"],
  activity_levels: ["low", "moderate", "high"],
  units: { energy: "kcal_per_day", protein: "g_per_day", weight: "kg" },
  daily: {
    "5-8": {
      label: "ages 5-8 (inclusive)",
      male: {
        protein_g: 21.4,
        energy_kcal: { low: 1450, moderate: 1645, high: 1950 },
      },
      female: {
        protein_g: 21.1,
        energy_kcal: { low: 1335, moderate: 1500, high: 1790 },
      },
    },
    "18-29": {
      label: "adults 18-30",
      male: {
        protein_g: 54,
        energy_kcal: { low: 2400, moderate: 2900, high: 3450 },
      },
      female: {
        protein_g: 46,
        energy_kcal: { low: 1900, moderate: 2300, high: 2650 },
      },
    },
    "60-plus": {
      label: "adults 60 and older",
      // a band whose sexed rows are missing → goal must resolve to nulls
    },
  },
  source: { s1: "S1", s2: "S2", verified: "2026-10-28" },
  caveats: ["population averages"],
};

describe("defaultProfile", () => {
  it("picks the first served value of every list", () => {
    expect(defaultProfile(GOALS)).toEqual({
      ageBand: "5-8",
      sex: "male",
      activityLevel: "low",
    });
  });

  it("is null without goal data", () => {
    expect(defaultProfile(null)).toBeNull();
  });
});

describe("resolveGoal", () => {
  it("resolves the served WHO value for the stored profile", () => {
    const goal = resolveGoal(
      GOALS,
      { ageBand: "18-29", sex: "male", activityLevel: "moderate" },
      null
    );
    expect(goal).toEqual({
      kcal: 2900,
      proteinG: 54,
      source: "who",
      defaulted: false,
      profile: { ageBand: "18-29", sex: "male", activityLevel: "moderate" },
    });
  });

  it("without a stored profile, resolves the first-served default and marks it", () => {
    const goal = resolveGoal(GOALS, null, null);
    expect(goal.source).toBe("who");
    expect(goal.defaulted).toBe(true);
    expect(goal.kcal).toBe(1450);
    expect(goal.proteinG).toBe(21.4);
    expect(goal.profile).toEqual({
      ageBand: "5-8",
      sex: "male",
      activityLevel: "low",
    });
  });

  it("the user's override always wins and is labelled custom", () => {
    const goal = resolveGoal(
      GOALS,
      { ageBand: "18-29", sex: "male", activityLevel: "moderate" },
      { kcal: 2100, proteinG: 60 }
    );
    expect(goal).toEqual({
      kcal: 2100,
      proteinG: 60,
      source: "custom",
      defaulted: false,
      profile: null,
    });
  });

  it("a non-positive override is ignored (falls back to the served value)", () => {
    const goal = resolveGoal(GOALS, null, { kcal: 0, proteinG: 60 });
    expect(goal.source).toBe("who");
    expect(goal.kcal).toBe(1450);
  });

  it("the override works even while goal data has not loaded", () => {
    const goal = resolveGoal(null, null, { kcal: 2000, proteinG: 55 });
    expect(goal.source).toBe("custom");
    expect(goal.kcal).toBe(2000);
  });

  it("no goal data and no override → source none, null shares", () => {
    expect(resolveGoal(null, null, null)).toEqual({
      kcal: null,
      proteinG: null,
      source: "none",
      defaulted: false,
      profile: null,
    });
  });

  it("an unknown band or missing sexed row resolves to null values, never invented ones", () => {
    const unknownBand = resolveGoal(
      GOALS,
      { ageBand: "30-59", sex: "male", activityLevel: "moderate" },
      null
    );
    expect(unknownBand.kcal).toBeNull();
    expect(unknownBand.proteinG).toBeNull();

    const missingRow = resolveGoal(
      GOALS,
      { ageBand: "60-plus", sex: "female", activityLevel: "moderate" },
      null
    );
    expect(missingRow.kcal).toBeNull();
    expect(missingRow.proteinG).toBeNull();
  });
});

describe("shareOfGoal", () => {
  it("divides the meal value by the goal", () => {
    expect(shareOfGoal(600, 2000)).toBeCloseTo(0.3);
  });

  it("is null whenever the meal or goal is missing or non-positive", () => {
    expect(shareOfGoal(null, 2000)).toBeNull();
    expect(shareOfGoal(600, null)).toBeNull();
    expect(shareOfGoal(600, 0)).toBeNull();
    expect(shareOfGoal(600, -5)).toBeNull();
  });
});
