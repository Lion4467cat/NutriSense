import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import { PREFS_KEY } from "../context/prefs";
import { createMemoryStorage } from "../services/storage";
import type { ApiClient } from "../services/api";
import type { MenuResponse } from "../types/api";
import AnalyzePage from "./Analyze";

const MENU: MenuResponse = {
  dishes: {},
  days: { mon: { label: "Monday" } },
  bands: {
    "1-5": {
      kcal: { direction: "min", value: 450 },
      protein_g: { direction: "min", value: 12 },
    },
  },
  capture_fields: {
    serving_style: { values: ["mixed", "single"] },
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
  getHealth: () => Promise.resolve({ status: "ok", phase: "built" }),
  analyze: () => Promise.reject(new Error("not used")),
};

function renderAnalyze(mode: "school" | "general" = "school", apiClient: ApiClient = client) {
  const storage = createMemoryStorage({
    [PREFS_KEY]: JSON.stringify({ mode }),
  });
  return render(
    <AppProvider storage={storage} client={apiClient}>
      <MemoryRouter>
        <AnalyzePage />
      </MemoryRouter>
    </AppProvider>
  );
}

describe("AnalyzePage meal-structure selection", () => {
  it("does not ask School-mode users to choose a serving style", async () => {
    renderAnalyze("school");

    expect(await screen.findByLabelText("Day")).toBeInTheDocument();
    expect(screen.getByLabelText("Class band")).toBeInTheDocument();
    expect(screen.queryByLabelText("Serving style")).not.toBeInTheDocument();
    expect(screen.getByText(/chooses the analysis path automatically/i)).toBeInTheDocument();
  });

  it("does not ask General-mode users to choose a serving style", async () => {
    renderAnalyze("general");

    expect(await screen.findByText(/chooses the analysis path automatically/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Serving style")).not.toBeInTheDocument();
  });

  it("keeps unsupported uploads out of the request and explains how to recover", async () => {
    const analyze = vi.fn(() => Promise.reject(new Error("must not run")));
    renderAnalyze("school", { ...client, analyze });
    const input = await screen.findByLabelText("Upload meal photo");
    fireEvent.change(input, {
      target: { files: [new File(["gif"], "meal.gif", { type: "image/gif" })] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("JPEG or PNG");
    expect(screen.getByRole("button", { name: "Analyze this meal" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(analyze).not.toHaveBeenCalled();
  });
});
