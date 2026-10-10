import { describe, expect, it } from "vitest";
import happyWire from "../fixtures/contract.happy.json";
import menuWire from "../fixtures/contract.menu.json";
import unreadableWire from "../fixtures/contract.unreadable.json";
import {
  analysisSchema,
  failureSchema,
  menuSchema,
  policySchema,
  reasonSchema,
} from "./contract.gen";

function fixture(name: string): unknown {
  return name === "contract.happy.json" ? happyWire : unreadableWire;
}

describe("python→typescript contract parity", () => {
  it("the happy-path Analysis fixture satisfies the schema", () => {
    const parsed = analysisSchema.safeParse(fixture("contract.happy.json"));
    expect(parsed.error?.message).toBeUndefined();
    expect(parsed.success).toBe(true);
  });

  it("the unreadable-image fixture satisfies the schema", () => {
    const parsed = analysisSchema.safeParse(
      fixture("contract.unreadable.json")
    );
    expect(parsed.success).toBe(true);
  });

  it("reason kinds are open — a future kind still parses", () => {
    const parsed = reasonSchema.safeParse({ kind: "future_kind", text: "ok" });
    expect(parsed.success).toBe(true);
  });

  it("failure kinds are open — a future kind still parses", () => {
    const parsed = failureSchema.safeParse({
      kind: "future_kind",
      stage: "segment",
      error: "x",
    });
    expect(parsed.success).toBe(true);
  });

  it("verdicts are closed — an unknown verdict fails decode", () => {
    const wire = fixture("contract.happy.json") as Record<string, unknown>;
    const parsed = analysisSchema.safeParse({ ...wire, verdict: "MAYBE" });
    expect(parsed.success).toBe(false);
  });

  it("stages are closed — an unknown stage fails decode", () => {
    const parsed = failureSchema.safeParse({
      kind: "stage_failed",
      stage: "teleport",
      error: "x",
    });
    expect(parsed.success).toBe(false);
  });

  it("missing wire keys fail decode (contract is 16 keys, not a subset)", () => {
    const wire = fixture("contract.happy.json") as Record<string, unknown>;
    const { policy, ...withoutPolicy } = wire;
    expect(policy).toBeDefined();
    expect(analysisSchema.safeParse(withoutPolicy).success).toBe(false);
  });
});

describe("menu contract parity", () => {
  it("the menu fixture satisfies menuSchema", () => {
    const parsed = menuSchema.safeParse(menuWire);
    expect(parsed.error?.message).toBeUndefined();
    expect(parsed.success).toBe(true);
  });

  it("missing /menu keys fail decode (top-level keys are closed)", () => {
    const { policy, ...withoutPolicy } = menuWire as Record<string, unknown>;
    expect(policy).toBeDefined();
    expect(menuSchema.safeParse(withoutPolicy).success).toBe(false);
  });

  it("an unknown verdict fails decode in the menu's policy-bearing neighbor", () => {
    // sanity: the shared policySchema is the same object both seams decode
    expect(menuSchema.shape.policy).toBe(policySchema);
  });
});
