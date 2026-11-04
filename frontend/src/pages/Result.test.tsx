import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Route, Routes, MemoryRouter } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import ResultPage from "./Result";
import { KEY, type AnalysisRecord } from "../services/records";
import { createMemoryStorage } from "../services/storage";
import type { ApiClient } from "../services/api";
import type { MenuResponse } from "../types/api";
import type { AnalyzeResult } from "../types/api";
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
    // differs from the fixture record's stored digest → earlier-policy note
    policy_version: "current-v9",
  },
};

const stubClient: ApiClient = {
  base: "http://test",
  getMenu: () => Promise.resolve(MENU),
  getGoals: () => Promise.reject(new Error("down")),
  getHealth: () => Promise.reject(new Error("down")),
  analyze: () => Promise.reject(new Error("unused")),
};

const fixtureResult = happy as unknown as AnalyzeResult;

const fixtureRecord: AnalysisRecord = {
  id: "fixture-rec",
  createdAt: "2026-10-05T12:00:00.000Z",
  day: "mon",
  band: "1-5",
  serving_style: "mixed",
  student: null,
  photo: null,
  summary: {
    verdict: fixtureResult.verdict,
    dish: fixtureResult.dish?.display_name || null,
    grams: fixtureResult.portion?.grams ?? null,
    kcal: fixtureResult.nutrition?.kcal?.mean ?? null,
    protein: fixtureResult.nutrition?.protein_g?.mean ?? null,
    coverage: fixtureResult.coverage?.score ?? null,
    confidence: fixtureResult.classification?.confidence ?? null,
  },
  result: fixtureResult,
};

function renderResult(record = fixtureRecord) {
  const storage = createMemoryStorage({
    [KEY]: JSON.stringify([record]),
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

describe("ResultPage from a fixture record", () => {
  it("renders the stored analysis (happy-path wire fixture)", async () => {
    renderResult();
    expect(await screen.findAllByText("Rice & Sambar")).not.toHaveLength(0);
    expect(screen.getAllByText("Borderline").length).toBeGreaterThan(0);
    expect(screen.getByText(/1 food region detected/)).toBeInTheDocument();
  });

  it("shows the automatically detected multi-region count", async () => {
    const record: AnalysisRecord = {
      ...fixtureRecord,
      result: {
        ...fixtureResult,
        path_used: "multi_item",
        segmentation: {
          strategy: fixtureResult.segmentation?.strategy ?? null,
          sam_score: fixtureResult.segmentation?.sam_score ?? null,
          area_frac: fixtureResult.segmentation?.area_frac ?? null,
          n_candidates: fixtureResult.segmentation?.n_candidates ?? null,
          n_items: 2,
        },
      },
    };
    renderResult(record);
    expect(await screen.findByText(/2 food regions detected/)).toBeInTheDocument();
  });

  it("shows one-serving fallback when region count is omitted", async () => {
    const record: AnalysisRecord = {
      ...fixtureRecord,
      result: {
        ...fixtureResult,
        segmentation: {
          strategy: fixtureResult.segmentation?.strategy ?? null,
          sam_score: fixtureResult.segmentation?.sam_score ?? null,
          area_frac: fixtureResult.segmentation?.area_frac ?? null,
          n_candidates: fixtureResult.segmentation?.n_candidates ?? null,
        },
      },
    };
    renderResult(record);
    expect(await screen.findByText(/Analyzed as one serving/)).toBeInTheDocument();
  });

  it("maps a reason kind to its icon (below_min → bad ✕)", async () => {
    renderResult();
    // the first reason text also appears in VerdictCard — take the list row
    const matches = await screen.findAllByText(
      "kcal: P=0.16 < 0.9 pass zone"
    );
    const text = matches.find((el) => el.closest(".reason-item"));
    expect(text).toBeDefined();
    const row = text!.closest(".reason-item");
    expect(row).not.toBeNull();
    const icon = row!.querySelector(".r-ico");
    expect(icon).toHaveClass("bad");
    expect(icon).toHaveTextContent("✕");
  });

  it("shows the policy note for the fixture (its policy differs from current)", async () => {
    renderResult();
    expect(
      await screen.findByText("judged under an earlier policy")
    ).toBeInTheDocument();
  });
});
