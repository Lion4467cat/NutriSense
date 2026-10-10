import { describe, expect, it } from "vitest";
import { reasonTone, verdictMeta, VERDICT_META } from "./verdicts";

describe("reasonTone", () => {
  it("maps closed kinds without consulting the verdict or prose", () => {
    expect(reasonTone({ kind: "in_zone", text: "…" }, "FAIL")).toBe("good");
    expect(reasonTone({ kind: "below_min", text: "…" }, "PASS")).toBe("bad");
    expect(reasonTone({ kind: "stage_failed", text: "…" }, "PASS")).toBe("bad");
    expect(reasonTone({ kind: "coverage_gate", text: "…" }, "PASS")).toBe("info");
  });

  it("defaults open-vocabulary kinds to the neutral glyph", () => {
    expect(reasonTone({ kind: "some_future_kind", text: "…" }, "PASS")).toBe("info");
  });

  it("derives legacy tones from the structured verdict, never the prose", () => {
    const prose = { kind: "legacy" as const };
    expect(reasonTone({ ...prose, text: "all mandatory nutrients passed" }, "FAIL")).toBe("bad");
    expect(reasonTone({ ...prose, text: "fail zone, below minimum, failed" }, "PASS")).toBe("good");
    expect(reasonTone({ ...prose, text: "anything" }, "BORDERLINE")).toBe("info");
    expect(reasonTone({ ...prose, text: "anything" }, "cannot_verify")).toBe("info");
    expect(reasonTone({ ...prose, text: "anything" }, "out_of_scope")).toBe("info");
  });
});

describe("verdictMeta", () => {
  it("covers every closed verdict", () => {
    expect(Object.keys(VERDICT_META)).toHaveLength(5);
  });

  it("falls back to cannot_verify for unknown or missing verdicts", () => {
    expect(verdictMeta("BOGUS").key).toBe("cannot_verify");
    expect(verdictMeta(undefined).key).toBe("cannot_verify");
    expect(verdictMeta(null).key).toBe("cannot_verify");
  });
});
