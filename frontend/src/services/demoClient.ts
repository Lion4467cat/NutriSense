import demoAnalysisFixture from "../fixtures/contract.happy.json";
import demoMenuFixture from "../fixtures/contract.menu.json";
import {
  analysisSchema,
  goalsSchema,
  healthSchema,
  menuSchema,
  type Analysis,
} from "../types/contract.gen";
import { mealCritiqueSchema } from "../types/mealCoach";
import type { ApiClient, AnalyzeParams } from "./api";

const demoGoals = goalsSchema.parse({
  age_bands: ["10-14", "15-18"],
  sexes: ["female", "male"],
  activity_levels: ["low", "moderate", "high"],
  units: { energy: "kcal/day", protein: "g/day", weight: "kg" },
  daily: {
    "10-14": {
      label: "Demo age band",
      female: {
        protein_g: 45,
        energy_kcal: { low: 1800, moderate: 2100, high: 2400 },
      },
      male: {
        protein_g: 50,
        energy_kcal: { low: 2000, moderate: 2300, high: 2600 },
      },
    },
    "15-18": {
      label: "Demo age band",
      female: {
        protein_g: 50,
        energy_kcal: { low: 1900, moderate: 2200, high: 2500 },
      },
      male: {
        protein_g: 60,
        energy_kcal: { low: 2300, moderate: 2700, high: 3100 },
      },
    },
  },
  source: { s1: "Fixed demonstration values", s2: "Not for nutrition guidance" },
  caveats: ["Demo goal values are illustrative and are not served nutrition guidance."],
});

function demoResponse(params: AnalyzeParams): Analysis {
  const source = analysisSchema.parse(demoAnalysisFixture);
  const sourceItem = source.items?.[0];
  if (!sourceItem?.portion || !sourceItem.dish || !sourceItem.classification) {
    throw new Error("The demo analysis fixture is missing an item template.");
  }

  const itemSpecs = [
    { name: "Steamed rice", id: "steamed_rice", grams: 250, sigma: 0.18, area: 0.34 },
    { name: "Sambar", id: "sambar", grams: 135, sigma: 0.24, area: 0.23 },
    { name: "Vegetable salad", id: "salad", grams: 75, sigma: 0.31, area: 0.12 },
  ] as const;
  const contextDay = params.mode === "general" ? "general" : params.day;
  const contextBand = params.mode === "general" ? "general" : params.band;
  const dishContext = {
    day: contextDay,
    band: contextBand,
    serving_style: params.serving_style ?? null,
  };
  const items = itemSpecs.map((spec, index) => ({
    ...sourceItem,
    dish: {
      ...sourceItem.dish!,
      ...dishContext,
      id: spec.id,
      display_name: spec.name,
      nutrition_source: "demo_sample",
    },
    classification: {
      ...sourceItem.classification!,
      dish: spec.id,
      confidence: 0.94 - index * 0.04,
      method: "demo_sample",
      reason: "Fixed demonstration response; the uploaded pixels were not classified.",
    },
    portion: {
      ...sourceItem.portion!,
      grams: spec.grams,
      volume_ml: Math.round(spec.grams / sourceItem.portion!.density_eff),
      components_g: { [spec.id]: spec.grams },
      base_method: "demo_sample",
      sigma_grams_rel: spec.sigma,
      sigma_rel: { demo_sample: spec.sigma },
      flags: ["demo_sample"],
    },
    bbox: [80 + index * 90, 120, 220 + index * 90, 350] as [number, number, number, number],
    area_frac: spec.area,
    sam_score: 0.93 - index * 0.05,
  }));
  const totalGrams = itemSpecs.reduce((sum, item) => sum + item.grams, 0);

  return analysisSchema.parse({
    ...source,
    verdict: params.mode === "general" ? "ESTIMATED" : source.verdict,
    dish: source.dish ? {
      ...source.dish,
      ...dishContext,
      nutrition_source: "demo_sample",
    } : null,
    classification: source.classification ? {
      ...source.classification,
      confidence: 0.91,
      method: "mock",
      reason: "Fixed demonstration response; the uploaded pixels were not classified.",
    } : null,
    anchor: source.anchor ? {
      ...source.anchor,
      method: "demo_sample",
      tier: "demo",
      reason: "Fixed sample; no reference marker was analyzed.",
    } : null,
    lint: null,
    compliance: params.mode === "general" ? null : source.compliance ? {
      ...source.compliance,
      ...dishContext,
      nutrients: {
        ...source.compliance.nutrients,
        kcal: { ...source.compliance.nutrients.kcal, min: params.band === "1-5" ? 450 : 700 },
        protein_g: { ...source.compliance.nutrients.protein_g, min: params.band === "1-5" ? 12 : 20 },
      },
    } : null,
    assumptions: [
      "Fixed multi-item demo response; the uploaded photo was not analyzed.",
      "Nutrition values and uncertainty ranges are illustrative.",
    ],
    model_versions: {
      segmenter: "mock",
      classifier: "mock",
      depth: "mock",
      runtime: "fixed-demo-v1",
    },
    segmentation: {
      ...source.segmentation,
      strategy: "demo_sample",
      n_candidates: items.length,
      n_items: items.length,
    },
    path_used: "multi_item",
    items,
    portion: {
      ...source.portion!,
      grams: totalGrams,
      volume_ml: Math.round(totalGrams / source.portion!.density_eff),
      components_g: Object.fromEntries(itemSpecs.map((item) => [item.id, item.grams])),
      base_method: "demo_sample",
      sigma_grams_rel: 0.16,
      sigma_rel: { demo_sample: 0.16 },
      flags: ["demo_sample"],
      grams_source: "demo_sample",
    },
    nutrition: {
      ...source.nutrition!,
      grams: {
        mean: totalGrams,
        sd: 60,
        p05: 360,
        p50: 455,
        p95: 560,
        interval_90: [360, 560],
      },
    },
  });
}

const sampleMenu = menuSchema.parse(demoMenuFixture);
const sampleGoals = goalsSchema.parse(demoGoals);

export function createDemoClient(): ApiClient {
  return {
    base: "demo://local",
    demo: true,
    getMenu: async () => sampleMenu,
    getGoals: async () => sampleGoals,
    getHealth: async () => healthSchema.parse({ status: "ok", phase: "demo" }),
    analyze: async (params: AnalyzeParams) => {
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      const sample = demoResponse(params);
      return analysisSchema.parse(JSON.parse(JSON.stringify(sample)));
    },
    critiqueMeal: async () => mealCritiqueSchema.parse({
      overview: "This is a fixed demo critique, not personalized advice.",
      add: ["Try pairing the meal with a fruit or another colorful vegetable."],
      reduce: ["No reduction is suggested by this sample."],
      caveat: "Demo content only; no meal photo or personal data was analyzed.",
    }),
    chatAboutMeal: async (_analysis, _history, message) =>
      `Demo reply to “${message}”: this response is fixed sample text, not model-generated advice.`,
  };
}
