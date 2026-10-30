import { describe, expect, it, vi } from "vitest";
import menuFixture from "../fixtures/contract.menu.json";
import { ApiError, createClient } from "./api";

function ok(data: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => data,
  } as Response;
}

describe("api client wire decode", () => {
  it("getMenu decodes /menu against the generated schema", async () => {
    const fetch = vi.fn(async () => ok(menuFixture));
    const client = createClient({
      base: "http://test",
      fetch: fetch as unknown as typeof globalThis.fetch,
    });
    const menu = await client.getMenu();
    expect(menu.policy.policy_version).toMatch(/^[0-9a-f]{12}$/);
    expect(Object.keys(menu.bands).length).toBeGreaterThan(0);
  });

  it("menu drift fails as a decode error, never renders garbage", async () => {
    const fetch = vi.fn(async () => ok({ dishes: {} }));
    const client = createClient({
      base: "http://test",
      fetch: fetch as unknown as typeof globalThis.fetch,
    });
    await expect(client.getMenu()).rejects.toThrow(ApiError);
    await expect(client.getMenu()).rejects.toThrow(
      "The backend returned an unexpected response."
    );
  });

  it("getHealth decodes {status, phase}", async () => {
    const fetch = vi.fn(async () => ok({ status: "ok", phase: "built" }));
    const client = createClient({
      base: "http://test",
      fetch: fetch as unknown as typeof globalThis.fetch,
    });
    await expect(client.getHealth()).resolves.toEqual({
      status: "ok",
      phase: "built",
    });
  });

  it("getGoals decodes the /goals wire (age bands, served daily table, caveats)", async () => {
    const goalsWire = {
      age_bands: ["5-8", "18-29"],
      sexes: ["male", "female"],
      activity_levels: ["low", "moderate", "high"],
      units: { energy: "kcal_per_day", protein: "g_per_day", weight: "kg" },
      daily: {
        "18-29": {
          label: "adults 18-30 (S1 band 18-29.9)",
          male: {
            referent_weight_kg: 65,
            protein_g_per_kg_day: 0.83,
            protein_g: 54,
            energy_kcal: { low: 2400, moderate: 2900, high: 3450 },
            status: { energy: "literature", protein: "literature" },
            provenance: { energy: "direct: S1", protein: "direct: S2" },
          },
          female: {
            referent_weight_kg: 55,
            protein_g_per_kg_day: 0.83,
            protein_g: 46,
            energy_kcal: { low: 1900, moderate: 2300, high: 2650 },
            status: { energy: "literature", protein: "literature" },
            provenance: { energy: "direct: S1", protein: "direct: S2" },
          },
        },
      },
      source: {
        s1: "FAO/WHO/UNU 2004",
        s2: "WHO TRS 935 (2007)",
        verified: "2026-10-28",
      },
      caveats: ["population-group averages"],
    };
    const fetch = vi.fn(async () => ok(goalsWire));
    const client = createClient({
      base: "http://test",
      fetch: fetch as unknown as typeof globalThis.fetch,
    });
    const goals = await client.getGoals();
    expect(goals.age_bands).toEqual(["5-8", "18-29"]);
    expect(goals.daily["18-29"].male?.energy_kcal?.moderate).toBe(2900);
    expect(goals.sexes).toEqual(["male", "female"]);
    expect(goals.caveats).toHaveLength(1);
  });

  it("goals drift fails as a decode error, never renders garbage", async () => {
    const fetch = vi.fn(async () => ok({ age_bands: ["5-8"] }));
    const client = createClient({
      base: "http://test",
      fetch: fetch as unknown as typeof globalThis.fetch,
    });
    await expect(client.getGoals()).rejects.toThrow(ApiError);
    await expect(client.getGoals()).rejects.toThrow(
      "The backend returned an unexpected response."
    );
  });
});
