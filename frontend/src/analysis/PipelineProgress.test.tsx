import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PipelineProgress from "./PipelineProgress";

describe("analysis progress disclosure", () => {
  it("does not claim live pipeline stages completed when the API streams no events", () => {
    render(<PipelineProgress running />);
    expect(screen.getByText("Analyzing meal")).toBeInTheDocument();
    expect(screen.getByText(/Detailed stage progress is not streamed/)).toBeInTheDocument();
    expect(screen.queryByText("Segmenting food")).not.toBeInTheDocument();
    expect(screen.queryByText("done")).not.toBeInTheDocument();
  });

  it("marks demo progress as illustrative", () => {
    render(<PipelineProgress running demo />);
    expect(screen.getByText(/Preparing demo result/)).toBeInTheDocument();
    expect(screen.getByText(/does not inspect the uploaded pixels or run inference models/)).toBeInTheDocument();
  });
});
