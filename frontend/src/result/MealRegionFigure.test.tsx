import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ItemBlock } from "../types/contract.gen";
import MealRegionFigure from "./MealRegionFigure";

const items = [
  { bbox: [100, 80, 300, 240] },
  { bbox: [700, 500, 1100, 900] },
] as ItemBlock[];

function loadPhoto(container: HTMLElement) {
  const image = container.querySelector("img")!;
  Object.defineProperties(image, {
    naturalWidth: { configurable: true, value: 1200 },
    naturalHeight: { configurable: true, value: 1200 },
  });
  fireEvent.load(image);
}

describe("MealRegionFigure", () => {
  it("draws only valid pixel-coordinate bounds and numbers them", () => {
    const { container } = render(<MealRegionFigure photo="meal.jpg" items={items} />);
    loadPhoto(container);
    expect(screen.getByRole("img", { name: /2 returned food region bounds/ })).toBeInTheDocument();
    expect(container.querySelectorAll(".meal-region-box")).toHaveLength(2);
    expect(container.querySelectorAll(".meal-region-markers li")).toHaveLength(2);
    expect(screen.getByText(/rectangles do not represent pixel masks/)).toBeInTheDocument();
  });

  it("never paints fixed demo regions over the uploaded photo", () => {
    const { container } = render(<MealRegionFigure photo="uploaded.jpg" items={items} demo />);
    loadPhoto(container);
    expect(container.querySelector(".meal-region-svg")).not.toBeInTheDocument();
    expect(screen.getByText("Captured meal")).toBeInTheDocument();
  });
});
