/**
 * View vocabulary for the NutriSense wire (GET /health, GET /menu,
 * POST /analyze). Every shape is DERIVED from the generated Zod schemas in
 * contract.gen.ts — Python owns the wire (tools/gen_contract_ts.py renders
 * it; ADR-0001). This module only aliases the generated names so views keep
 * their vocabulary; the hand-typed mirror is gone.
 *
 * Exception: AnalyzeResult stays Partial for LEGACY STORED records only —
 * the wire itself is decoded by analysisSchema in services/api.ts.
 */

import type { Analysis, Policy, Reason, Verdict } from "./contract.gen";

export type {
  AdvisoryBlock as Advisory,
  AnchorBlock as Anchor,
  BandStandard,
  CaptureField,
  ClassificationBlock as Classification,
  CoverageBlock as Coverage,
  DayMenu,
  DishBlock as DishInfo,
  Failure,
  HealthResponse,
  Lint,
  MenuItem,
  MenuResponse,
  NutritionBlock as Nutrition,
  NutrientRow,
  NutrientSummary,
  Policy,
  PortionBlock as Portion,
  Reason,
  SegmentationBlock as Segmentation,
  Verdict,
} from "./contract.gen";

export type ClassBand = "1-5" | "6-8" | "9-10";
export type DayKey = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | string;

/** The full 16-key /analyze payload (engine.contract.Analysis). */
export type AnalyzeResponse = Analysis;

/**
 * Legacy stored records (nutrisense.records.v1/v2) may predate later wire
 * keys — Partial applies ONLY at the storage boundary; adaptV1Record in
 * services/records.ts is the adapter. Fresh responses are Analysis.
 */
export type AnalyzeResult = Partial<Analysis> & {
  verdict: Verdict;
  reasons: Reason[];
};

/** Pre-policy records (and a down /menu) render with today's constants. */
export const FALLBACK_POLICY: Policy = {
  pass_p: 0.9,
  fail_p: 0.1,
  pass_min: 0.85,
  fail_min: 0.9,
  anchor_prior_cap: 0.6,
  base_table_prior: 0.85,
  quality_degraded: 0.9,
  depth_uncalibrated: 0.8,
  lint_min_side_px: 1280,
  policy_version: "unknown",
};
