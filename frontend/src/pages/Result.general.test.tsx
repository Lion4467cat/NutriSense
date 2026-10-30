import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Route, Routes, MemoryRouter } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import { PREFS_KEY } from "../context/prefs";
import ResultPage from "./Result";
import { KEY, type AnalysisRecord } from "../services/records";
import { createMemoryStorage } from "../services/storage";
import type { ApiClient } from "../services/api";
import type { GoalsResponse, MenuResponse, AnalyzeResult } from "../types/api";
import happy from "../fixtures/contract.happy.json";

const MENU: MenuResponse = {
  dishes: {},
  days: {},
  bands: {},
  capture_fields: {
    serving_style: { values: ["mixed"] },
    day: { values: ["mon"] },
    band: { values: ["1-5"] },
  },
  remarks: [],
  policy: {
    pass_p: 0.9,
    fail_p: 0.1,
    pass_min: 0.85,
    fail_min: 0.9,
    anchor_prior_cap: 0.6,
    estimated_weight: 0.9,
    base_table_prior: 0.85,
    quality_degraded: 0.9,
    depth_uncalibrated: 0.8,
    lint_min_side_px: 1280,
    policy_version: "current-v9",
  },
};

/** Mirrors the GET /goals wire for the profile the tests store in prefs. */
const GOALS: GoalsResponse = {
  age_bands: ["5-8", "18-29"],
  sexes: ["male", "female"],
  activity_levels: ["low", "moderate", "high"],
  units: { energy: "kcal_per_day", protein: "g_per_day", weight: "kg" },
  daily: {
    "5-8": {
      male: { protein_g: 21.4, energy_kcal: { low: 1450, moderate: 1645, high: 1950 } },
      female: { protein_g: 21.1, energy_kcal: { low: 1335, moderate: 1500, high: 1790 } },
    },
    "18-29": {
      male: { protein_g: 54, energy_kcal: { low: 2400, moderate: 2900, high: 3450 } },
      female: { protein_g: 46, energy_kcal: { low: 1900, moderate: 2300, high: 2650 } },
    },
  },
  source: { s1: "S1", s2: "S2", verified: "2026-10-28" },
  caveats: [],
};

const stubClient: ApiClient = {
  base: "http://test",
  getMenu: () => Promise.resolve(MENU),
  getGoals: () => Promise.resolve(GOALS),
  getHealth: () => Promise.reject(new Error("down")),
  analyze: () => Promise.reject(new Error("unused")),
};

const fixtureResult = happy as unknown as AnalyzeResult;

function makeRecord(
  id: string,
  result: AnalyzeResult,
  patch: Partial<AnalysisRecord["summary"]> = {}
): AnalysisRecord {
  return {
    id,
    createdAt: "2026-10-05T12:00:00.000Z",
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    student: null,
    photo: null,
    summary: {
      verdict: result.verdict,
      dish: result.dish?.display_name || null,
      grams: result.portion?.grams ?? null,
      kcal: result.nutrition?.kcal?.mean ?? null,
      protein: result.nutrition?.protein_g?.mean ?? null,
      coverage: result.coverage?.score ?? null,
      confidence: result.classification?.confidence ?? null,
      ...patch,
    },
    result,
  };
}

function renderGeneral(result: AnalyzeResult) {
  const storage = createMemoryStorage({
    [KEY]: JSON.stringify([makeRecord("fixture-rec", result)]),
    [PREFS_KEY]: JSON.stringify({
      mode: "general",
      profile: { ageBand: "18-29", sex: "male", activityLevel: "moderate" },
    }),
  });
  return render(
    <AppProvider storage={storage} client={stubClient}>
      <MemoryRouter initialEntries={["/result/fixture-rec"]}>
        <Routes>
          <Route path="/result/:id" element={<ResultPage />} />
        </Routes>
      </MemoryRouter>
    </AppProvider>
  );
}

describe("ResultPage in General mode (spec 002)", () => {
  it("renders grams + nutrients + goal shares and NO verdict badge", async () => {
    renderGeneral(fixtureResult);
    // the meal is shown as a share of the WHO goal (390.8 kcal of 2900 → 13%)
    expect(
      await screen.findByText(/13% of your day/)
    ).toBeInTheDocument();
    expect(screen.getByText("Share of your Daily goal")).toBeInTheDocument();
    // no compliance verdict anywhere, and no school machinery
    expect(screen.queryByText("BORDERLINE")).not.toBeInTheDocument();
    expect(screen.queryByText(/PM POSHAN minimum/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText("judged under an earlier policy")
    ).not.toBeInTheDocument();
  });

  it("labels classifier confidence and gallery match score as separate values", async () => {
    const result: AnalyzeResult = {
      ...fixtureResult,
      classification: {
        ...fixtureResult.classification!,
        confidence: 0.35,
        match_score: 0.945,
        method: "gallery",
      },
    };
    renderGeneral(result);

    expect(
      await screen.findAllByText(/classifier confidence 35%/i)
    ).not.toHaveLength(0);
    expect(screen.getByText(/confidence=0\.35 · match_score=0\.945/)).toBeInTheDocument();
    expect(screen.queryByText(/recognition confidence/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Measurement details"));
    expect(screen.getByText("Classifier confidence")).toBeInTheDocument();
    expect(screen.getByText("Gallery match score")).toBeInTheDocument();
    expect(screen.getByText("0.945")).toBeInTheDocument();
  });

  it("keeps the no-card estimate disclaimer leading when the backend sent it", async () => {
    const result: AnalyzeResult = {
      ...fixtureResult,
      verdict: "cannot_verify",
      reasons: [
        {
          kind: "no_reference_card",
          text: "No reference card — this photo has no measured scale, so its weight is an estimate",
        },
        ...fixtureResult.reasons,
      ],
    };
    renderGeneral(result);
    expect(
      await screen.findByText("Estimated weight — no reference card")
    ).toBeInTheDocument();
  });

  it("renders a recognized off-menu dish with an honest note, not an error state", async () => {
    const result: AnalyzeResult = {
      ...fixtureResult,
      verdict: "cannot_verify",
      reasons: [
        {
          kind: "off_menu_dish",
          text: "recognized off-menu dish rajma — not on the school menu, so no compliance verdict; grams and nutrients are provided",
        },
        {
          kind: "no_reference_card",
          text: "No reference card — this photo has no measured scale, so its weight is an estimate",
        },
      ],
    };
    renderGeneral(result);
    expect(
      await screen.findByText("Not a school-menu dish — no compliance verdict")
    ).toBeInTheDocument();
    // the estimates still render beside the note
    expect(screen.getByText("Share of your Daily goal")).toBeInTheDocument();
    expect(screen.queryByText("BORDERLINE")).not.toBeInTheDocument();
  });

  it("an unrecognized capture shows why there are no numbers", async () => {
    const result: AnalyzeResult = {
      verdict: "out_of_scope",
      reasons: [{ kind: "unrecognized", text: "could not recognize a dish" }],
      failures: [],
      policy: {
        pass_p: 0.9,
        fail_p: 0.1,
        pass_min: 0.85,
        fail_min: 0.9,
        anchor_prior_cap: 0.6,
        estimated_weight: 0.9,
        base_table_prior: 0.85,
        quality_degraded: 0.9,
        depth_uncalibrated: 0.8,
        lint_min_side_px: 1280,
        policy_version: "current-v9",
      },
      model_versions: {},
      assumptions: [],
      degradations: [],
    };
    renderGeneral(result);
    expect(await screen.findByText("No nutrition estimate")).toBeInTheDocument();
    expect(
      screen.getByText(/could not recognize a dish in this photo/i)
    ).toBeInTheDocument();
    expect(screen.queryByText("Share of your Daily goal")).not.toBeInTheDocument();
  });
});
