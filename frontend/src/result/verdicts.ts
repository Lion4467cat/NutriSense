import type { Reason, Verdict } from "../types/api";
import type { ComponentType } from "react";
import { IconAlert, IconCheck, IconHelp, IconLayers, IconScale, IconX } from "../ui/Icon";

/* ---------------- verdict meta — single truth ---------------- */

export interface VerdictMeta {
  key: Verdict;
  label: string;
  icon: ComponentType<{ size?: number }>;
  cls: "pass" | "warn" | "fail" | "neutral";
  blurb: string;
}

export const VERDICT_META: Record<Verdict, VerdictMeta> = {
  PASS: {
    key: "PASS",
    label: "Pass",
    icon: IconCheck,
    cls: "pass",
    blurb: "Meal meets the required nutrition threshold with sufficient coverage.",
  },
  BORDERLINE: {
    key: "BORDERLINE",
    label: "Borderline",
    icon: IconAlert,
    cls: "warn",
    blurb: "Probabilities are close to a threshold, or coverage is short of the gate.",
  },
  FAIL: {
    key: "FAIL",
    label: "Fail",
    icon: IconX,
    cls: "fail",
    blurb: "Mandatory nutrition is below the required minimum with sufficient coverage.",
  },
  ESTIMATED: {
    key: "ESTIMATED",
    label: "Estimated",
    icon: IconScale,
    cls: "neutral",
    blurb: "An estimate is available, but uncertain food labels or item boundaries prevent a reliable school-compliance verdict.",
  },
  cannot_verify: {
    key: "cannot_verify",
    label: "Cannot verify",
    icon: IconHelp,
    cls: "neutral",
    blurb: "The capture could not be verified — check capture quality and try again.",
  },
  out_of_scope: {
    key: "out_of_scope",
    label: "Out of scope",
    icon: IconLayers,
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
  estimate_only: "info",
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
 * neutral glyph; `legacy` (v1 pre-contract string reasons) falls back to the
 * record's structured verdict — prose is never parsed.
 */
export function reasonTone(reason: Reason, verdict: Verdict | string): Tone {
  const known = KIND_TONE[reason.kind];
  if (known) return known;
  if (reason.kind !== "legacy") return "info"; // open vocabulary: default glyph
  const cls = verdictMeta(verdict).cls;
  return cls === "pass" ? "good" : cls === "fail" ? "bad" : "info";
}
