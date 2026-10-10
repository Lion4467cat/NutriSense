import { STAGE_NAMES, type StageName } from "../types/contract.gen";

/**
 * Labels for every stage of the generated wire vocabulary — typed
 * Record<StageName, …> so a backend stage addition fails tsc until
 * both UIs label it.
 */

/** Short gerunds for the PipelineProgress step list. */
export const STAGE_LABELS: Record<StageName, string> = {
  input: "Checking image",
  anchor: "Detecting scale",
  segment: "Segmenting food",
  classify: "Identifying dish",
  depth: "Estimating depth",
  portion: "Estimating portion",
  nutrition: "Calculating nutrition",
  compliance: "Evaluating compliance",
};

/** Descriptive copy for the Analyze "How it works" card. */
export const HOW_IT_WORKS: Record<StageName, string> = {
  input: "Image checked (resolution, EXIF)",
  anchor: "Scale detected (card / prior)",
  segment: "Food segmented (SAM 2.1)",
  classify: "Dish identified (SigLIP2 gallery)",
  depth: "Depth calibrated (MoGe-2)",
  portion: "Portion estimated in grams",
  nutrition: "Nutrients sampled 4000× (Monte Carlo)",
  compliance: "PM POSHAN compliance evaluated",
};

export const STAGES = STAGE_NAMES.map((stage) => ({
  stage,
  label: STAGE_LABELS[stage],
}));
