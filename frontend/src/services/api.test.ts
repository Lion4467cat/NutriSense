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
});
