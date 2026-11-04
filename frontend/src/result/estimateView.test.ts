import { describe, expect, it } from "vitest";
import happyFixture from "../fixtures/contract.happy.json";
import { analysisSchema } from "../types/contract.gen";
import { itemWeightView, mealWeightView } from "./estimateView";

const analysis = analysisSchema.parse(happyFixture);

describe("meal estimate display projection", () => {
  it("uses the aggregate meal-weight interval when available", () => {
    const view = mealWeightView(analysis);
    expect(view?.grams).toBe(analysis.nutrition?.grams.mean);
    expect(view?.interval90).toEqual(analysis.nutrition?.grams.interval_90);
  });

  it("does not invent a meal interval when only portion sigma is available", () => {
    const view = mealWeightView({ ...analysis, nutrition: null });
    expect(view?.grams).toBe(analysis.portion?.grams);
    expect(view?.interval90).toBeNull();
    expect(view?.relativeSd).toBe(analysis.portion?.sigma_grams_rel);
  });

  it("keeps item-level relative SD separate from meal intervals", () => {
    const item = analysis.items?.[0];
    expect(item).toBeDefined();
    expect(itemWeightView(item!).relativeSdPercent).toBeCloseTo(
      (item?.portion?.sigma_grams_rel ?? 0) * 100,
    );
  });
});
