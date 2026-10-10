import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { PREFS_KEY, PrefsProvider, usePrefs } from "./prefs";
import { RecordsProvider, useRecords } from "./records";
import { KEY, MAX_RECORDS, type AnalysisRecord } from "../services/records";
import { createMemoryStorage, type Storage } from "../services/storage";
import type { AnalyzeResult } from "../types/api";

function makeRecord(id: string, createdAt: string): AnalysisRecord {
  return {
    id,
    createdAt,
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    student: null,
    photo: null,
    summary: {
      verdict: "BORDERLINE",
      dish: "Rice & Sambar",
      grams: 300,
      kcal: 400,
      protein: 12,
      coverage: 0.7,
      confidence: 0.9,
    },
    result: {
      verdict: "BORDERLINE",
      reasons: [],
      policy: { policy_version: "current-v9" },
    } as unknown as AnalyzeResult,
  };
}

function iso(minuteOffset: number): string {
  return new Date(Date.UTC(2026, 0, 1, 12, 0, minuteOffset * 60)).toISOString();
}

let storage: Storage;

beforeEach(() => {
  storage = createMemoryStorage();
});

describe("usePrefs", () => {
  it("returns defaults when the injected storage is empty", () => {
    const { result } = renderHook(() => usePrefs(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <PrefsProvider storage={storage}>{children}</PrefsProvider>
      ),
    });
    expect(result.current.prefs).toEqual({
      theme: "system",
      accent: "indigo",
      userName: "",
      defaultDay: "",
      defaultBand: "",
    });
  });

  it("loads seeded prefs from the injected storage", () => {
    storage.set(
      PREFS_KEY,
      JSON.stringify({ accent: "teal", userName: "Ada", defaultDay: "tue" })
    );
    const { result } = renderHook(() => usePrefs(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <PrefsProvider storage={storage}>{children}</PrefsProvider>
      ),
    });
    expect(result.current.prefs.accent).toBe("teal");
    expect(result.current.prefs.userName).toBe("Ada");
    expect(result.current.prefs.defaultDay).toBe("tue");
    // untouched keys keep their defaults
    expect(result.current.prefs.theme).toBe("system");
  });

  it("setPrefs merges and persists through the injected storage", () => {
    storage.set(PREFS_KEY, JSON.stringify({ accent: "teal" }));
    const { result } = renderHook(() => usePrefs(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <PrefsProvider storage={storage}>{children}</PrefsProvider>
      ),
    });
    act(() => result.current.setPrefs({ theme: "midnight" }));
    expect(result.current.prefs.theme).toBe("midnight");
    expect(result.current.prefs.accent).toBe("teal");
    expect(JSON.parse(storage.get(PREFS_KEY)!)).toEqual({
      accent: "teal",
      theme: "midnight",
      userName: "",
      defaultDay: "",
      defaultBand: "",
    });
    // the real localStorage is never involved
    expect(window.localStorage.getItem(PREFS_KEY)).toBeNull();
  });
});

describe("useRecords", () => {
  const recordsWrapper =
    (s: Storage) =>
    ({ children }: { children: ReactNode }) => (
      <RecordsProvider storage={s}>{children}</RecordsProvider>
    );

  it("reads seeded records from the injected storage", () => {
    storage.set(
      KEY,
      JSON.stringify([
        makeRecord("rec-2", iso(20)),
        makeRecord("rec-1", iso(10)),
      ])
    );
    const { result } = renderHook(() => useRecords(), {
      wrapper: recordsWrapper(storage),
    });
    expect(result.current.records.map((r) => r.id)).toEqual([
      "rec-2",
      "rec-1",
    ]);
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it("addRecord persists through the injected storage", () => {
    const { result } = renderHook(() => useRecords(), {
      wrapper: recordsWrapper(storage),
    });
    act(() => result.current.addRecord(makeRecord("new-1", iso(1))));
    expect(result.current.records.map((r) => r.id)).toEqual(["new-1"]);
    const stored = JSON.parse(storage.get(KEY)!);
    expect(stored.map((r: AnalysisRecord) => r.id)).toEqual(["new-1"]);
  });

  it("addRecord caps at MAX_RECORDS, evicting the oldest", () => {
    const seeded = Array.from({ length: MAX_RECORDS }, (_, i) =>
      makeRecord(`r${String(i).padStart(3, "0")}`, iso(i))
    );
    storage.set(KEY, JSON.stringify(seeded));
    const { result } = renderHook(() => useRecords(), {
      wrapper: recordsWrapper(storage),
    });
    act(() =>
      result.current.addRecord(makeRecord("r200-newest", iso(MAX_RECORDS)))
    );
    expect(result.current.records).toHaveLength(MAX_RECORDS);
    expect(result.current.records[0].id).toBe("r200-newest");
    expect(result.current.records.map((r) => r.id)).not.toContain("r000");
    const stored = JSON.parse(storage.get(KEY)!);
    expect(stored).toHaveLength(MAX_RECORDS);
    expect(stored[0].id).toBe("r200-newest");
  });

  it("removeRecord and clearRecords persist through the injected storage", () => {
    storage.set(
      KEY,
      JSON.stringify([
        makeRecord("keep", iso(20)),
        makeRecord("drop", iso(10)),
      ])
    );
    const { result } = renderHook(() => useRecords(), {
      wrapper: recordsWrapper(storage),
    });
    act(() => result.current.removeRecord("drop"));
    expect(result.current.records.map((r) => r.id)).toEqual(["keep"]);
    expect(
      JSON.parse(storage.get(KEY)!).map((r: AnalysisRecord) => r.id)
    ).toEqual(["keep"]);

    act(() => result.current.clearRecords());
    expect(result.current.records).toEqual([]);
    expect(storage.get(KEY)).toBe("[]");
  });
});
