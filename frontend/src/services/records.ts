import type { AnalyzeResult, Verdict } from "../types/api";
import { toReasons } from "../utils/reasons";
import type { Storage } from "./storage";

/**
 * Local analysis store.
 *
 * The backend does not persist analyses today, so the frontend keeps a
 * browser-local history (through an injected Storage — localStorage in
 * production, memory in tests) that a future history endpoint can replace —
 * the shape below is the record the UI reads from.
 *
 * v2 records carry the wire policy block; v1 stays untouched as a read-only
 * backup after migration (standards.yaml remains the policy source of truth).
 */

export interface RecordStudent {
  name: string;
}

export interface RecordSummary {
  verdict: Verdict;
  dish: string | null;
  grams: number | null;
  kcal: number | null;
  protein: number | null;
  coverage: number | null;
  confidence: number | null;
}

export interface AnalysisRecord {
  id: string;
  createdAt: string;
  day: string;
  band: string;
  serving_style: string;
  student: RecordStudent | null;
  photo: string | null;
  summary: RecordSummary;
  result: AnalyzeResult;
}

export const KEY = "nutrisense.records.v2";
export const LEGACY_KEY = "nutrisense.records.v1";
export const MAX_RECORDS = 200;

function createdAtMs(r: AnalysisRecord): number {
  const t = Date.parse(r?.createdAt ?? "");
  return Number.isFinite(t) ? t : 0;
}

/** Newest first; records with unparseable dates sort as oldest. */
export function capRecords(records: AnalysisRecord[]): AnalysisRecord[] {
  return [...records]
    .sort((a, b) => createdAtMs(b) - createdAtMs(a))
    .slice(0, MAX_RECORDS);
}

function isValidRecord(r: unknown): r is AnalysisRecord {
  return !!r && typeof r === "object" && typeof (r as AnalysisRecord).id === "string";
}

/**
 * v1 → v2 adapter: accept a pre-contract record, normalise its reasons to
 * {kind, text} objects, keep everything else (missing `policy` is legal —
 * the UI notes it under an earlier policy). Returns null for junk.
 */
export function adaptV1Record(raw: unknown): AnalysisRecord | null {
  if (!isValidRecord(raw)) return null;
  const rec: AnalysisRecord = { ...raw };
  if (rec.result && typeof rec.result === "object") {
    rec.result = {
      ...rec.result,
      reasons: toReasons((rec.result as AnalyzeResult).reasons),
    };
  }
  return rec;
}

function parseKey(storage: Storage, key: string): AnalysisRecord[] {
  try {
    const raw = storage.get(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isValidRecord);
  } catch {
    return [];
  }
}

export function loadRecords(storage: Storage): AnalysisRecord[] {
  const v2 = parseKey(storage, KEY);
  if (v2.length > 0 || storage.get(KEY) !== null) {
    return capRecords(v2);
  }
  // first run after the migration: adapt v1 once, write v2, never touch v1
  const legacy = parseKey(storage, LEGACY_KEY);
  if (legacy.length === 0) return [];
  const migrated = capRecords(
    legacy.map(adaptV1Record).filter((r): r is AnalysisRecord => r !== null)
  );
  saveRecords(storage, migrated);
  return migrated;
}

export function saveRecords(storage: Storage, records: AnalysisRecord[]): void {
  const capped = capRecords(records);
  try {
    storage.set(KEY, JSON.stringify(capped));
  } catch {
    /* storage full — drop thumbnails from oldest entries and retry once */
    try {
      const slim = capped.map((r, i) => (i < 30 ? r : { ...r, photo: null }));
      storage.set(KEY, JSON.stringify(slim));
    } catch {
      /* give up silently — history is a convenience, never data-critical */
    }
  }
}

export function makeRecord(input: {
  day: string;
  band: string;
  serving_style: string;
  student: RecordStudent | null;
  photo: string | null;
  result: AnalyzeResult;
}): AnalysisRecord {
  const r = input.result;
  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    day: input.day,
    band: input.band,
    serving_style: input.serving_style,
    student: input.student,
    photo: input.photo,
    summary: {
      verdict: r.verdict,
      dish: r.dish?.display_name || r.classification?.dish || null,
      grams: r.portion?.grams ?? null,
      kcal: r.nutrition?.kcal?.mean ?? null,
      protein: r.nutrition?.protein_g?.mean ?? null,
      coverage: r.coverage?.score ?? null,
      confidence: r.classification?.confidence ?? null,
    },
    result: r,
  };
}

/** Downscale an image to a small JPEG data URL for local thumbnails. */
export function fileToThumbnail(file: File, maxSide = 220): Promise<string | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
      const w = Math.max(1, Math.round(img.width * scale));
      const h = Math.max(1, Math.round(img.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        URL.revokeObjectURL(url);
        resolve(null);
        return;
      }
      ctx.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", 0.6));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(null);
    };
    img.src = url;
  });
}
