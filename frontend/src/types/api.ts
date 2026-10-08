/**
 * Types mirroring the actual NutriSense backend responses
 * (GET /health, GET /menu, POST /analyze). Grounded in engine/pipeline.py,
 * engine/compliance.py, engine/mc.py and main.py — no invented fields.
 */

export type Verdict =
  | "PASS"
  | "FAIL"
  | "BORDERLINE"
  | "cannot_verify"
  | "out_of_scope";

export type ClassBand = "1-5" | "6-8" | "9-10";
export type DayKey = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | string;

export interface Lint {
  digital_zoom: number | null;
  focal_mm: number | null;
  min_side_px: number;
  resolution_ok: boolean;
  notes: string[];
}

export interface Anchor {
  method: string;
  tier: "measured" | "prior" | string;
  cm_per_px: number | null;
  interval: [number | null, number | null] | null;
  tilt_deg: number | null;
  reason: string;
  depth_scale_factor?: number;
  depth_scale_source?: string;
}

export interface Segmentation {
  strategy: string | null;
  sam_score: number | null;
  area_frac: number | null;
  n_candidates: number | null;
}

export interface Classification {
  dish: string | null;
  confidence: number | null;
  method: string | null;
  match_score: number | null;
  reason: string | null;
}

export interface DishInfo {
  id: string;
  display_name: string;
  day: string;
  band: string;
  serving_style?: string | null;
  on_day: boolean;
  nutrition_source: string;
}

export interface Portion {
  grams: number;
  volume_ml: number;
  density_eff: number;
  components_g: Record<string, number>;
  base_method: string;
  scale_tier: string;
  mean_h_mm: number;
  area_cm2: number;
  sigma_grams_rel: number;
  sigma_rel: Record<string, number>;
  flags: string[];
}

export interface NutrientSummary {
  mean: number;
  sd: number;
  p05: number;
  p50: number;
  p95: number;
  interval_90: [number, number];
}

export interface Nutrition {
  kcal: NutrientSummary;
  protein_g: NutrientSummary;
  grams: number;
  n: number;
  seed: number;
  diagnostics: Record<string, unknown>;
  assumed_nutrients: string[];
  wider_ranges: boolean;
}

export interface Coverage {
  score: number;
  factors: Record<string, number>;
  pass_min: number;
  fail_min: number;
}

export interface NutrientRow {
  min: number;
  p_at_or_above_min: number;
  mean: number;
  interval_90: [number, number];
  headroom_at_interval_low: number;
}

export interface Compliance {
  day: string;
  band: string;
  probs: Record<string, number>;
  nutrients: Record<string, NutrientRow>;
}

export interface Advisory {
  sodium_salt?: {
    direction?: string;
    primary_g: number;
    upper_g: number;
    note?: string;
  };
  note?: string;
}

/**
 * Full /analyze payload. `unreadable image` responses only carry
 * verdict+reasons, so every detail block is optional at the type level.
 */
export interface AnalyzeResponse {
  verdict: Verdict;
  reasons: string[];
  lint: Lint | null;
  anchor: Anchor | null;
  segmentation: Segmentation | null;
  classification: Classification | null;
  dish: DishInfo | null;
  portion: Portion | null;
  nutrition: Nutrition | null;
  coverage: Coverage | null;
  assumptions: string[];
  advisory: Advisory | null;
  compliance: Compliance | null;
  model_versions: Record<string, string>;
}

export type AnalyzeResult = Partial<AnalyzeResponse> & {
  verdict: Verdict;
  reasons: string[];
};

export interface HealthResponse {
  status: string;
  phase: string;
}

export interface BandStandard {
  classes?: string;
  kcal: { direction: string; value: number };
  protein_g: { direction: string; value: number };
}

export interface DayMenu {
  note?: string;
  vegetables?: string[];
}

export interface MenuItem {
  display_name?: string;
  days?: string[];
  aliases?: string[];
  subtype?: string;
  nutrition_source?: string;
  status?: string;
  standard_class?: string;
  components?: Record<string, unknown>;
  ranges_wider?: boolean;
  mandatory_report_line?: string;
  [key: string]: unknown;
}

export interface CaptureField {
  type?: string;
  values: string[];
  note?: string;
}

export interface MenuResponse {
  dishes: Record<string, MenuItem>;
  days: Record<string, DayMenu>;
  bands: Record<string, BandStandard>;
  capture_fields: {
    serving_style: CaptureField;
    day: CaptureField;
    band: CaptureField;
  };
  remarks: string[];
}
