import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Collapse } from "./primitives";

describe("Collapse", () => {
  it("animates open and closes after its content transition", () => {
    const { container } = render(
      <Collapse summary="Measurement details"><p>Measured detail</p></Collapse>
    );
    const details = container.querySelector("details")!;
    const body = container.querySelector(".collapse-body")!;

    fireEvent.click(screen.getByText("Measurement details"));
    expect(details.open).toBe(true);
    expect(body).toHaveClass("is-open");

    fireEvent.click(screen.getByText("Measurement details"));
    expect(details.open).toBe(true);
    expect(body).not.toHaveClass("is-open");
    fireEvent.transitionEnd(body, { propertyName: "grid-template-rows" });
    expect(details.open).toBe(false);
  });
});
