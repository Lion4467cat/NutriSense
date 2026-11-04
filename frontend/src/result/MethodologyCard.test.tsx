import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { AnalyzeResult } from "../types/api";
import happy from "../fixtures/contract.happy.json";
import MethodologyCard from "./MethodologyCard";

const result = happy as unknown as AnalyzeResult;

describe("MethodologyCard capture check", () => {
  it("explains that missing zoom metadata withholds the school verdict", () => {
    render(
      <MethodologyCard
        result={{
          ...result,
          lint: { ...result.lint!, digital_zoom: null, resolution_ok: true },
        }}
      />,
    );

    expect(
      screen.getByText(
        "Photo is large enough, but zoom metadata is missing. Food identification can continue; the school-standard verdict is withheld.",
      ),
    ).toBeInTheDocument();
    const captureRow = screen.getByText("1 · Capture check").closest(".method-row");
    expect(captureRow?.querySelector(".method-dot")).toHaveClass("warn");
  });

  it("marks a sufficiently large, explicitly unzoomed photo as ready", () => {
    render(
      <MethodologyCard
        result={{
          ...result,
          lint: { ...result.lint!, digital_zoom: 1, resolution_ok: true },
        }}
      />,
    );

    expect(
      screen.getByText(
        "Photo is large enough, and its metadata reports no digital zoom.",
      ),
    ).toBeInTheDocument();
    const captureRow = screen.getByText("1 · Capture check").closest(".method-row");
    expect(captureRow?.querySelector(".method-dot")).toHaveClass("ok");
  });

  it("explains the limits of WED semantic regions", () => {
    render(
      <MethodologyCard
        result={{
          ...result,
          segmentation: {
            strategy: "wed_deeplabv3_semantic",
            sam_score: null,
            area_frac: 0.42,
            n_candidates: 9,
            n_items: 4,
          },
        }}
      />,
    );

    expect(
      screen.getByText(
        "The frozen WED model labels food pixels by class. Connected regions are provisional class proposals, not verified serving instances.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/semantic class regions=4/)).toBeInTheDocument();
  });
});
