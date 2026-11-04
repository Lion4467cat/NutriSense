import type { Reason } from "../types/api";

/**
 * Reasons are {kind, text} objects on the wire (engine.contract). Records
 * saved before the contract carried plain strings — normalise both so every
 * consumer can render `reason.text` without crashing.
 */
export function toReasons(raw: unknown): Reason[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((r): Reason => {
    if (typeof r === "string") return { kind: "legacy", text: r };
    if (r && typeof r === "object") {
      const o = r as Partial<Reason>;
      if (typeof o.text === "string") {
        return { kind: typeof o.kind === "string" ? o.kind : "legacy", text: o.text };
      }
    }
    return { kind: "legacy", text: String(r) };
  });
}

/** Short, human-readable explanations for reasons returned by the pipeline. */
export function explainReason(reason: Reason): string {
  switch (reason.kind) {
    case "zoom":
      return "Digital zoom was detected. It can reduce portion measurement accuracy.";
    case "unknown_day":
      return "This photo could not be matched to a school service day.";
    case "unknown_band":
      return "This photo could not be matched to a class band.";
    case "out_of_scope":
      return "This dish is outside the school menu used for this analysis.";
    case "unrecognized":
      return "The meal could not be identified with enough confidence.";
    case "estimate_only":
      return "A tentative meal estimate is shown. The system did not issue a compliance verdict.";
    case "unreadable":
      return "The photo could not be read. Try a clear photo of the full plate.";
    case "stage_failed":
      if (reason.text.includes("four-item limit")) {
        return "The region detector found more food areas than the analyzer can safely measure in one meal.";
      }
      if (reason.text.includes("Detected food regions overlap")) {
        return "The detected food regions overlap, so their portions cannot be measured separately.";
      }
      return "The analysis could not be completed with enough reliable evidence. See the reason below.";
    case "in_zone":
      return "All required nutrients fall within the target range.";
    case "below_min":
      if (reason.text.startsWith("kcal:")) return "Energy falls below the target range.";
      if (reason.text.startsWith("protein_g:")) return "Protein falls below the target range.";
      if (reason.text.startsWith("iron_mg:")) return "Iron falls below the target range.";
      if (reason.text.startsWith("calcium_mg:")) return "Calcium falls below the target range.";
      return "At least one required nutrient falls below the minimum target.";
    case "coverage_gate":
      return "Coverage is below the level needed for a reliable verdict.";
    case "no_reference_card":
      return "No reference card was detected. Portion weight is estimated from the photo.";
    case "weight_head_unavailable":
      return "The portion weight could not be estimated from this photo.";
    case "off_menu_dish":
      return "This dish is not listed on the selected school menu, so no school meal verdict is shown.";
    default:
      return reason.text;
  }
}

export function firstReasonText(raw: unknown): string | undefined {
  const reason = toReasons(raw)[0];
  return reason ? explainReason(reason) : undefined;
}
