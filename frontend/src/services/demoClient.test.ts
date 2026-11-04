import { describe, expect, it, vi } from "vitest";
import { analysisSchema } from "../types/contract.gen";
import { createDemoClient } from "./demoClient";

describe("local demo client", () => {
  it("returns a schema-valid multi-item sample without fetching or loading models", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const client = createDemoClient();
    const result = await client.analyze({
      file: new File(["image bytes"], "meal.jpg", { type: "image/jpeg" }),
      day: "mon",
      band: "1-5",
      mode: "school",
    });

    expect(client.demo).toBe(true);
    expect(analysisSchema.safeParse(result).success).toBe(true);
    expect(result.model_versions.segmenter).toBe("mock");
    expect(result.items).toHaveLength(3);
    expect(result.nutrition?.grams.mean).toBe(460);
    expect(result.items?.reduce((sum, item) => sum + (item.portion?.grams ?? 0), 0)).toBe(460);
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("serves valid offline menu, goal, health, critique, and chat responses", async () => {
    const client = createDemoClient();
    const result = await client.analyze({
      file: new File(["image bytes"], "meal.jpg", { type: "image/jpeg" }),
      day: "mon",
      band: "1-5",
    });

    expect((await client.getMenu()).days.mon).toBeDefined();
    expect((await client.getGoals()).daily["10-14"].female?.protein_g).toBe(45);
    expect(await client.getHealth()).toEqual({ status: "ok", phase: "demo" });
    await expect(client.critiqueMeal?.(result)).resolves.toMatchObject({
      overview: expect.stringContaining("fixed demo"),
    });
    await expect(client.chatAboutMeal?.(result, [], "why?")).resolves.toContain("fixed sample");
  });

  it("keeps selected school context and removes school compliance in General mode", async () => {
    const client = createDemoClient();
    const file = new File(["image bytes"], "meal.jpg", { type: "image/jpeg" });
    const school = await client.analyze({ file, day: "wed", band: "6-8", mode: "school" });
    expect(school.dish?.day).toBe("wed");
    expect(school.dish?.band).toBe("6-8");
    expect(school.compliance?.day).toBe("wed");
    expect(school.compliance?.band).toBe("6-8");

    const general = await client.analyze({ file, day: "mon", band: "1-5", mode: "general" });
    expect(general.verdict).toBe("ESTIMATED");
    expect(general.compliance).toBeNull();
  });
});
