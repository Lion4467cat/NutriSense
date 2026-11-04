import { describe, expect, it } from "vitest";
import { captureFileError, MAX_MEAL_IMAGE_BYTES } from "./useMealCapture";

describe("meal photo validation", () => {
  it("accepts JPEG and PNG files under the upload limit", () => {
    expect(captureFileError(new File(["jpeg"], "meal.jpg", { type: "image/jpeg" }))).toBeNull();
    expect(captureFileError(new File(["png"], "meal.png", { type: "image/png" }))).toBeNull();
  });

  it("rejects unsupported, empty, and oversized files with actionable messages", () => {
    expect(captureFileError(new File(["gif"], "meal.gif", { type: "image/gif" })))
      .toMatch(/JPEG or PNG/);
    expect(captureFileError(new File(["gif"], "meal.jpg", { type: "image/gif" })))
      .toMatch(/JPEG or PNG/);
    expect(captureFileError(new File([], "empty.png", { type: "image/png" })))
      .toMatch(/empty/);
    const large = new File(["x"], "large.jpg", { type: "image/jpeg" });
    Object.defineProperty(large, "size", { value: MAX_MEAL_IMAGE_BYTES + 1 });
    expect(captureFileError(large)).toMatch(/12 MB/);
  });
});
