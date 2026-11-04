import type { ItemBlock } from "../types/contract.gen";
import type { AnalyzeResult } from "../types/api";

export interface MealWeightView {
  grams: number;
  interval90: readonly [number, number] | null;
  volumeMl: number | null;
  relativeSd: number | null;
}

export interface ItemWeightView {
  grams: number | null;
  relativeSdPercent: number | null;
}

/** One place defines which wire estimate and uncertainty the UI presents. */
export function mealWeightView(result: AnalyzeResult): MealWeightView | null {
  const aggregate = result.nutrition?.grams;
  if (aggregate) {
    return {
      grams: aggregate.mean,
      interval90: aggregate.interval_90,
      volumeMl: result.portion?.volume_ml ?? null,
      relativeSd: result.portion?.sigma_grams_rel ?? null,
    };
  }
  const portion = result.portion;
  if (!portion) return null;
  return {
    grams: portion.grams,
    interval90: null,
    volumeMl: portion.volume_ml,
    relativeSd: portion.sigma_grams_rel,
  };
}

export function itemWeightView(item: ItemBlock): ItemWeightView {
  const portion = item.portion;
  return {
    grams: portion?.grams ?? null,
    relativeSdPercent: portion?.sigma_grams_rel == null
      ? null
      : portion.sigma_grams_rel * 100,
  };
}
