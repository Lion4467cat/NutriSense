import type { Reason, Verdict } from "../types/api";

/* ---------------- verdict meta — single truth ---------------- */

export interface VerdictMeta {
  key: Verdict;
  label: string;
  icon: string;
  cls: "pass" | "warn" | "fail" | "neutral";
  blurb: string;
}

export const VERDICT_META: Record<Verdict, VerdictMeta> = {
  PASS: {
    key: "PASS",
    label: "PASS",
    icon: "✓",
    cls: "pass",
    blurb: "Meal meets the required nutrition threshold with sufficient coverage.",
  },
  BORDERLINE: {
    key: "BORDERLINE",
    label: "BORDERLINE",
    icon: "!",
    cls: "warn",
    blurb: "Probabilities are close to a threshold, or coverage is short of the gate.",
  },
  FAIL: {
    key: "FAIL",
    label: "FAIL",
    icon: "✕",
    cls: "fail",
    blurb: "Mandatory nutrition is below the required minimum with sufficient coverage.",
  },
  cannot_verify: {
    key: "cannot_verify",
    label: "CANNOT VERIFY",
    icon: "?",
    cls: "neutral",
    blurb: "The capture could not be verified — check capture quality and try again.",
  },
  out_of_scope: {
    key: "out_of_scope",
    label: "OUT OF SCOPE",
    icon: "–",
    cls: "warn",
    blurb: "This item is not portion-scored under PM POSHAN compliance.",
  },
};

export function verdictMeta(v: string | undefined | null): VerdictMeta {
  return VERDICT_META[(v as Verdict) || "cannot_verify"] ?? VERDICT_META.cannot_verify;
}

/* ---------------- reason tones — single truth ---------------- */

export type Tone = "good" | "bad" | "info";

const KIND_TONE: Record<string, Tone> = {
  in_zone: "good",
  below_min: "bad",
  stage_failed: "bad",
  unrecognized: "bad",
  zoom: "bad",
  unknown_day: "bad",
  unknown_band: "bad",
  unreadable: "info",
  out_of_scope: "info",
  coverage_gate: "info",
};

/**
 * Icon tone for one reason. The closed kind map wins; unknown kinds get the
 * neutral glyph; `legacy` (v1 pre-contract strings) keeps its prose heuristics
 * because prose is all those stored records carry.
 */
export function reasonTone(reason: Reason): Tone {
  const known = KIND_TONE[reason.kind];
  if (known) return known;
  if (reason.kind !== "legacy") return "info"; // open vocabulary: default glyph
  // legacy v1 string reasons: keep the old prose heuristics
  const t = reason.text.toLowerCase();
  if (
    t.includes("fail zone") ||
    t.includes("below minimum") ||
    t.includes("<= 0.1") ||
    t.includes("< 0.9") ||
    t.includes("unrecognized") ||
    t.includes("failed") ||
    t.includes("unknown ")
  )
    return "bad";
  if (t.includes("all mandatory nutrients")) return "good";
  return "info";
}
