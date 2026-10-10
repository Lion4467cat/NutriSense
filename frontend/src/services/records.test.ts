import { beforeEach, describe, expect, it } from "vitest";
import {
  KEY,
  LEGACY_KEY,
  MAX_RECORDS,
  capRecords,
  loadRecords,
  saveRecords,
  type AnalysisRecord,
} from "./records";
import { createMemoryStorage, type Storage } from "./storage";
import type { AnalyzeResult } from "../types/api";

function makeRecord(
  id: string,
  createdAt: string,
  opts: { photo?: string | null; reasons?: unknown } = {}
): AnalysisRecord {
  const result = {
    verdict: "BORDERLINE",
    reasons: opts.reasons ?? [{ kind: "coverage_gate", text: "coverage below gate" }],
    policy: { policy_version: "v-current" },
  } as unknown as AnalyzeResult;
  return {
    id,
    createdAt,
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    student: null,
    photo: opts.photo ?? null,
    summary: {
      verdict: "BORDERLINE",
      dish: "Rice & Sambar",
      grams: 300,
      kcal: 400,
      protein: 12,
      coverage: 0.7,
      confidence: 0.9,
    },
    result,
  };
}

function iso(minuteOffset: number): string {
  return new Date(Date.UTC(2026, 0, 1, 12, 0, minuteOffset * 60)).toISOString();
}

let storage: Storage;

beforeEach(() => {
  storage = createMemoryStorage();
});

describe("v1 → v2 migration", () => {
  it("adapts legacy records into v2 and leaves v1 byte-identical", () => {
    const legacyRaw = JSON.stringify([
      {
        id: "old-1",
        createdAt: iso(1),
        day: "mon",
        band: "1-5",
        serving_style: "mixed",
        student: null,
        photo: "data:image/jpeg;base64,x",
        summary: {
          verdict: "FAIL",
          dish: null,
          grams: null,
          kcal: null,
          protein: null,
          coverage: null,
          confidence: null,
        },
        result: {
          verdict: "FAIL",
          reasons: ["coverage too low", "something else"],
          // pre-contract result: no policy block at all
        },
      },
      { not_a_record: true },
      {
        id: "old-2",
        createdAt: iso(5),
        day: "tue",
        band: "1-5",
        serving_style: "mixed",
        student: null,
        photo: null,
        summary: {
          verdict: "PASS",
          dish: null,
          grams: null,
          kcal: null,
          protein: null,
          coverage: null,
          confidence: null,
        },
        result: { verdict: "PASS", reasons: [{ kind: "coverage_ok", text: "ok" }] },
      },
    ]);
    storage.set(LEGACY_KEY, legacyRaw);

    const migrated = loadRecords(storage);

    expect(migrated.map((r) => r.id)).toEqual(["old-2", "old-1"]);
    const old1 = migrated.find((r) => r.id === "old-1")!;
    expect(old1.result.reasons).toEqual([
      { kind: "legacy", text: "coverage too low" },
      { kind: "legacy", text: "something else" },
    ]);
    const old2 = migrated.find((r) => r.id === "old-2")!;
    expect(old2.result.reasons).toEqual([
      { kind: "coverage_ok", text: "ok" },
    ]);

    // v1 is a read-only backup: untouched, byte for byte
    expect(storage.get(LEGACY_KEY)).toBe(legacyRaw);
    // v2 now exists and is what future loads read
    expect(storage.get(KEY)).not.toBeNull();
    const again = loadRecords(storage);
    expect(again.map((r) => r.id)).toEqual(["old-2", "old-1"]);
  });

  it("reads v2 directly when both keys exist (no re-migration)", () => {
    const v2 = [makeRecord("v2-rec", iso(10))];
    const v1 = [makeRecord("v1-rec", iso(20))];
    storage.set(KEY, JSON.stringify(v2));
    storage.set(LEGACY_KEY, JSON.stringify(v1));

    const loaded = loadRecords(storage);
    expect(loaded.map((r) => r.id)).toEqual(["v2-rec"]);
    expect(storage.get(LEGACY_KEY)).toBe(JSON.stringify(v1));
  });

  it("never touches the real window.localStorage", () => {
    storage.set(LEGACY_KEY, JSON.stringify([makeRecord("old", iso(1))]));
    loadRecords(storage);
    saveRecords(storage, [makeRecord("new", iso(2))]);
    expect(window.localStorage.getItem(KEY)).toBeNull();
    expect(window.localStorage.getItem(LEGACY_KEY)).toBeNull();
  });
});

describe("eviction", () => {
  it("keeps the 200 newest records and evicts exactly the 5 oldest", () => {
    // ids r000 (oldest) … r204 (newest), handed over in shuffled order
    const shuffled = Array.from({ length: 205 }, (_, i) =>
      makeRecord(`r${String(i).padStart(3, "0")}`, iso(i))
    ).reverse();

    saveRecords(storage, shuffled);

    const stored = JSON.parse(storage.get(KEY)!);
    expect(stored).toHaveLength(MAX_RECORDS);
    const ids = stored.map((r: AnalysisRecord) => r.id);
    // newest 200 survive: r005 … r204
    expect(ids[0]).toBe("r204");
    expect(ids[ids.length - 1]).toBe("r005");
    expect(ids).not.toContain("r000");
    expect(ids).not.toContain("r001");
    expect(ids).not.toContain("r002");
    expect(ids).not.toContain("r003");
    expect(ids).not.toContain("r004");
    // storage is newest-first: descending by zero-padded id
    expect(ids).toEqual([...ids].sort().reverse());
  });

  it("caps in-memory state the same way (capRecords keeps newest)", () => {
    const many = Array.from({ length: 205 }, (_, i) =>
      makeRecord(`r${String(i).padStart(3, "0")}`, iso(i))
    );
    const capped = capRecords(many);
    expect(capped).toHaveLength(MAX_RECORDS);
    expect(capped[0].id).toBe("r204");
    expect(capped[MAX_RECORDS - 1].id).toBe("r005");
  });

  it("on quota errors strips thumbnails from the oldest, keeping the newest 30", () => {
    const records = Array.from({ length: 40 }, (_, i) =>
      makeRecord(`r${String(i).padStart(3, "0")}`, iso(i), {
        photo: `data:image/jpeg;base64,${i}`,
      })
    );

    const mem = createMemoryStorage();
    let firstSet = true;
    const quotaStorage: Storage = {
      get: (k) => mem.get(k),
      set: (k, v) => {
        if (firstSet) {
          firstSet = false;
          throw new DOMException("QuotaExceededError");
        }
        mem.set(k, v);
      },
      remove: (k) => mem.remove(k),
    };

    saveRecords(quotaStorage, records);

    const stored = JSON.parse(quotaStorage.get(KEY)!);
    expect(stored).toHaveLength(40);
    // newest 30 (r039 … r010) keep their photo; the 10 oldest are stripped
    for (let i = 0; i < 30; i++) {
      expect(stored[i].photo).toBeTruthy();
      expect(stored[i].id).toBe(`r${String(39 - i).padStart(3, "0")}`);
    }
    for (let i = 30; i < 40; i++) {
      expect(stored[i].photo).toBeNull();
    }
  });
});
