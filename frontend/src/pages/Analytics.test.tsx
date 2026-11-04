import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import { KEY, type AnalysisRecord } from "../services/records";
import { PREFS_KEY } from "../context/prefs";
import { createMemoryStorage } from "../services/storage";
import type { ApiClient } from "../services/api";
import type { MenuResponse } from "../types/api";
import AnalyticsPage from "./Analytics";

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

const client: ApiClient = {
  base: "http://test",
  getMenu: () => Promise.resolve(MENU),
  getGoals: () => Promise.reject(new Error("not needed")),
  getHealth: () => Promise.reject(new Error("not needed")),
  analyze: () => Promise.reject(new Error("not needed")),
};

function record(id: string, mode: "school" | "general", dish: string, verdict: "PASS" | "ESTIMATED") {
  return {
    id,
    createdAt: "2026-11-01T12:00:00.000Z",
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    mode,
    student: null,
    photo: null,
    summary: {
      verdict,
      dish,
      grams: 300,
      kcal: 400,
      protein: 12,
      coverage: 0.8,
      confidence: 0.9,
    },
    result: { verdict, reasons: [] },
  } as unknown as AnalysisRecord;
}

function renderAnalytics(mode: "school" | "general") {
  const storage = createMemoryStorage({
    [PREFS_KEY]: JSON.stringify({ mode }),
    [KEY]: JSON.stringify([
      record("school-1", "school", "School porridge", "PASS"),
      record("general-1", "general", "Meal bowl", "ESTIMATED"),
    ]),
  });
  return render(
    <AppProvider storage={storage} client={client}>
      <MemoryRouter initialEntries={["/analytics"]}>
        <Routes>
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    </AppProvider>
  );
}

describe("AnalyticsPage mode boundaries", () => {
  it("shows general nutrition summaries without school compliance metrics", async () => {
    renderAnalytics("general");

    expect(await screen.findByText("Meals by dish")).toBeInTheDocument();
    expect(screen.getByText("Meal bowl")).toBeInTheDocument();
    expect(screen.queryByText("School porridge")).not.toBeInTheDocument();
    expect(screen.queryByText("Compliance rate")).not.toBeInTheDocument();
    expect(screen.queryByText("Verdict distribution")).not.toBeInTheDocument();
  });

  it("shows school compliance summaries without general meal records", async () => {
    renderAnalytics("school");

    expect(await screen.findByText("Dish comparison")).toBeInTheDocument();
    expect(screen.getByText("School porridge")).toBeInTheDocument();
    expect(screen.queryByText("Meal bowl")).not.toBeInTheDocument();
    expect(screen.getByText("Compliance rate")).toBeInTheDocument();
    expect(screen.getByText("Verdict distribution")).toBeInTheDocument();
  });
});
