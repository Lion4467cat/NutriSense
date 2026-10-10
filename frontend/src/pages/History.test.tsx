import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Route, Routes, MemoryRouter } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import HistoryPage from "./History";
import { KEY, type AnalysisRecord } from "../services/records";
import { createMemoryStorage } from "../services/storage";
import type { ApiClient } from "../services/api";
import type { MenuResponse } from "../types/api";

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
    base_table_prior: 0.85,
    quality_degraded: 0.9,
    depth_uncalibrated: 0.8,
    lint_min_side_px: 1280,
    policy_version: "current-v9",
  },
};

const stubClient: ApiClient = {
  base: "http://test",
  getMenu: () => Promise.resolve(MENU),
  getHealth: () => Promise.reject(new Error("down")),
  analyze: () => Promise.reject(new Error("unused")),
};

function makeRecord(
  id: string,
  createdAt: string,
  dish: string,
  policyVersion?: string
): AnalysisRecord {
  return {
    id,
    createdAt,
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    student: null,
    photo: null,
    summary: {
      verdict: "BORDERLINE",
      dish,
      grams: 300,
      kcal: 400,
      protein: 12,
      coverage: 0.7,
      confidence: 0.9,
    },
    result: {
      verdict: "BORDERLINE",
      reasons: [],
      ...(policyVersion !== undefined
        ? { policy: { policy_version: policyVersion } }
        : {}),
    } as unknown as AnalysisRecord["result"],
  };
}

function renderHistory(storage: ReturnType<typeof createMemoryStorage>) {
  return render(
    <AppProvider storage={storage} client={stubClient}>
      <MemoryRouter initialEntries={["/history"]}>
        <Routes>
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </MemoryRouter>
    </AppProvider>
  );
}

describe("HistoryPage from an injected in-memory Storage", () => {
  it("renders rows read from the injected storage (window.localStorage untouched)", async () => {
    const storage = createMemoryStorage({
      [KEY]: JSON.stringify([
        makeRecord("rec-current", "2026-10-02T12:00:00.000Z", "Rice & Sambar", "current-v9"),
        makeRecord("rec-legacy", "2026-10-01T12:00:00.000Z", "Vegetable Rice"),
      ]),
    });

    renderHistory(storage);

    expect(await screen.findByText("Rice & Sambar")).toBeInTheDocument();
    expect(screen.getByText("Vegetable Rice")).toBeInTheDocument();
    // data came through the injected Storage, not the real one
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it("notes only the row judged under an earlier policy", async () => {
    const storage = createMemoryStorage({
      [KEY]: JSON.stringify([
        makeRecord("rec-current", "2026-10-02T12:00:00.000Z", "Rice & Sambar", "current-v9"),
        makeRecord("rec-legacy", "2026-10-01T12:00:00.000Z", "Vegetable Rice"),
      ]),
    });

    renderHistory(storage);
    await screen.findByText("Vegetable Rice");

    // settles only when /menu has resolved: exactly one note, in the legacy row
    await waitFor(() => {
      const notes = screen.getAllByText("judged under an earlier policy");
      expect(notes).toHaveLength(1);
      const row = notes[0].closest("tr");
      expect(row).not.toBeNull();
      expect(row).toHaveTextContent("Vegetable Rice");
      expect(row).not.toHaveTextContent("Rice & Sambar");
    });
  });
});
