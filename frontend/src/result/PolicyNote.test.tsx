import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AppProvider } from "../context/AppContext";
import PolicyNote from "./PolicyNote";
import type { ApiClient } from "../services/api";
import type { MenuResponse } from "../types/api";
import { createMemoryStorage } from "../services/storage";
import type { AnalysisRecord } from "../services/records";

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

function recordWithPolicy(policyVersion?: string): AnalysisRecord {
  return {
    id: "rec-1",
    createdAt: "2026-01-01T12:00:00.000Z",
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    student: null,
    photo: null,
    summary: {
      verdict: "BORDERLINE",
      dish: null,
      grams: null,
      kcal: null,
      protein: null,
      coverage: null,
      confidence: null,
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

function renderNote(record: AnalysisRecord) {
  return render(
    <AppProvider storage={createMemoryStorage()} client={stubClient}>
      <PolicyNote record={record} />
    </AppProvider>
  );
}

describe("PolicyNote", () => {
  it("shows the note when the record's policy differs from the current one", async () => {
    renderNote(recordWithPolicy("older-v1"));
    expect(
      await screen.findByText("judged under an earlier policy")
    ).toBeInTheDocument();
  });

  it("shows the note for a migrated v1 record (no policy block)", async () => {
    renderNote(recordWithPolicy(undefined));
    expect(
      await screen.findByText("judged under an earlier policy")
    ).toBeInTheDocument();
  });

  it("shows no note when the record matches the current policy", async () => {
    renderNote(recordWithPolicy("current-v9"));
    await waitFor(() =>
      expect(
        screen.queryByText("judged under an earlier policy")
      ).toBeNull()
    );
  });
});
