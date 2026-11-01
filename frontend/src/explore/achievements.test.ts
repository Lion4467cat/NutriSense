import { describe, expect, it } from "vitest";
import { createMemoryStorage } from "../services/storage";
import {
  AREAS,
  EXPLORE_KEY,
  areaDepth,
  areaForPath,
  detectSecret,
  emptyExploration,
  levelFor,
  loadExploration,
  parseExploration,
  pointsFor,
  recordVisit,
  saveExploration,
  settle,
  unlockBadge,
} from "./achievements";

const NOON = new Date(2026, 10, 1, 12, 0, 0);
const NIGHT = new Date(2026, 10, 1, 23, 30, 0);
const NEXT_DAY = new Date(2026, 10, 2, 9, 0, 0);

function visitAll(days: Date[] = [NOON]) {
  return days.reduce(
    (state, day) => AREAS.reduce((s, area) => recordVisit(s, area.id, day), state),
    emptyExploration()
  );
}

describe("areaForPath", () => {
  it("maps every routed page onto an exploration area", () => {
    expect(areaForPath("/")).toBe("home");
    expect(areaForPath("/analyze")).toBe("analyze");
    expect(areaForPath("/result/abc")).toBe("history");
    expect(areaForPath("/history")).toBe("history");
    expect(areaForPath("/analytics")).toBe("insights");
    expect(areaForPath("/students/ada")).toBe("students");
    expect(areaForPath("/menu")).toBe("menu");
    expect(areaForPath("/settings")).toBe("settings");
    expect(areaForPath("/unknown")).toBe("home");
  });

  it("orders areas for the direction of the page transition", () => {
    expect(areaDepth("/")).toBeLessThan(areaDepth("/settings"));
    expect(areaDepth("/result/abc")).toBe(areaDepth("/history"));
  });
});

describe("recordVisit", () => {
  it("adds the area and the local calendar day once", () => {
    const first = recordVisit(emptyExploration(), "history", NOON);
    expect(first.areas).toEqual(["history"]);
    expect(first.days).toEqual(["2026-11-01"]);
    expect(recordVisit(first, "history", NOON)).toBe(first);
  });

  it("tracks distinct days without touching areas", () => {
    const first = recordVisit(emptyExploration(), "history", NOON);
    const second = recordVisit(first, "history", NEXT_DAY);
    expect(second.days).toEqual(["2026-11-01", "2026-11-02"]);
    expect(second.areas).toEqual(["history"]);
  });
});

describe("settle", () => {
  it("stays quiet on a single visit", () => {
    const state = recordVisit(emptyExploration(), "home", NOON);
    const { state: next, unlocked } = settle(state, NOON);
    expect(unlocked).toEqual([]);
    expect(next).toBe(state);
  });

  it("grants three-rooms on the third distinct area", () => {
    const state = ["home", "analyze", "history"].reduce(
      (s, id) => recordVisit(s, id as "home", NOON),
      emptyExploration()
    );
    expect(settle(state, NOON).unlocked).toEqual(["three-rooms"]);
  });

  it("grants the grand tour once every area is seen", () => {
    const { state, unlocked } = settle(visitAll(), NOON);
    expect(unlocked).toEqual(["three-rooms", "grand-tour"]);
    expect(settle(state, NOON).unlocked).toEqual([]);
  });

  it("grants night-shift for visits between 22:00 and 05:00", () => {
    const state = recordVisit(emptyExploration(), "home", NIGHT);
    expect(settle(state, NIGHT).unlocked).toContain("night-shift");
  });

  it("grants second helping when the app is opened on another day", () => {
    const state = recordVisit(
      recordVisit(emptyExploration(), "home", NOON),
      "home",
      NEXT_DAY
    );
    expect(settle(state, NEXT_DAY).unlocked).toEqual(["returning-visitor"]);
  });
});

describe("unlockBadge", () => {
  it("is idempotent and never reorders earned badges", () => {
    const once = unlockBadge(emptyExploration(), "konami");
    expect(once.badges).toEqual(["konami"]);
    expect(unlockBadge(once, "konami")).toBe(once);
    expect(unlockBadge(once, "logo-patter").badges).toEqual([
      "konami",
      "logo-patter",
    ]);
  });
});

describe("levels and points", () => {
  it("sums badge points", () => {
    const state = unlockBadge(unlockBadge(emptyExploration(), "three-rooms"), "konami");
    expect(pointsFor(state)).toBe(3);
  });

  it("walks the level ladder and reports the distance to the next one", () => {
    expect(levelFor(0).name).toBe("Taster");
    expect(levelFor(1).toNext).toBe(1);
    expect(levelFor(2).name).toBe("Forager");
    expect(levelFor(4).name).toBe("Explorer");
    expect(levelFor(7)).toEqual({ name: "Cartographer", index: 3, toNext: null });
  });
});

describe("persistence", () => {
  it("round-trips through the injected storage", () => {
    const storage = createMemoryStorage();
    const state = recordVisit(emptyExploration(), "menu", NOON);
    saveExploration(storage, state);
    expect(loadExploration(storage)).toEqual(state);
    expect(JSON.parse(storage.get(EXPLORE_KEY)!)).toEqual(state);
  });

  it("drops unknown ids and survives garbage", () => {
    expect(parseExploration("not json").badges).toEqual([]);
    expect(
      parseExploration(
        JSON.stringify({
          areas: ["home", "attic"],
          badges: ["konami", "trophy"],
          days: ["2026-11-01", 7],
        })
      )
    ).toEqual({ areas: ["home"], badges: ["konami"], days: ["2026-11-01"] });
  });
});

describe("detectSecret", () => {
  it("spots the konami sequence and clears the buffer", () => {
    const keys = ["arrowup", "arrowup", "arrowdown", "arrowdown", "arrowleft", "arrowright", "arrowleft"];
    const fed = keys.reduce(
      (acc, key) => detectSecret(acc.buffer, key),
      { secret: null as string | null, buffer: [] as string[] }
    );
    expect(fed.secret).toBeNull();
    const final = detectSecret(fed.buffer, "ArrowRight");
    expect(final.secret).toBe("konami");
    expect(final.buffer).toEqual([]);
  });

  it("spots the whisper word typed outside a field", () => {
    const fed = ["n", "u", "t", "r", "i"].reduce(
      (acc, key) => detectSecret(acc.buffer, key),
      { secret: null as string | null, buffer: [] as string[] }
    );
    expect(fed.secret).toBe("nutri-whisper");
  });

  it("ignores unrelated keys and keeps a bounded buffer", () => {
    const fed = "abcdefghijklmnopqrstuvwxyz".split("").reduce(
      (acc, key) => detectSecret(acc.buffer, key),
      { secret: null as string | null, buffer: [] as string[] }
    );
    expect(fed.secret).toBeNull();
    expect(fed.buffer.length).toBeLessThanOrEqual(8);
  });
});
