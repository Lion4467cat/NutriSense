import type { AnalyzeResult, Verdict } from "../types/api";
import { shareOfGoal } from "./goals";
import { localDateKey } from "../utils/format";
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
export function byNewest(records: AnalysisRecord[]): AnalysisRecord[] {
  return [...records].sort((a, b) => createdAtMs(b) - createdAtMs(a));
}

export function capRecords(records: AnalysisRecord[]): AnalysisRecord[] {
  return byNewest(records).slice(0, MAX_RECORDS);
}

/** Verdicts that carry a compliance score (excludes cannot_verify / out_of_scope). */
export const SCORED_VERDICTS: Verdict[] = ["PASS", "BORDERLINE", "FAIL"];

export function scored(records: AnalysisRecord[]): AnalysisRecord[] {
  return records.filter((r) => SCORED_VERDICTS.includes(r.summary.verdict));
}

export interface Tally {
  pass: number;
  warn: number;
  fail: number;
  /** PASS + BORDERLINE + FAIL — the scored denominator. */
  scored: number;
}

/** One verdict tally (P/B/F); unscored verdicts count nowhere. */
export function tally(records: AnalysisRecord[]): Tally {
  let pass = 0;
  let warn = 0;
  let fail = 0;
  for (const r of records) {
    if (r.summary.verdict === "PASS") pass += 1;
    else if (r.summary.verdict === "BORDERLINE") warn += 1;
    else if (r.summary.verdict === "FAIL") fail += 1;
  }
  return { pass, warn, fail, scored: pass + warn + fail };
}

/** Verdicts a human should look at again. */
export const ATTENTION_VERDICTS: Verdict[] = [
  "FAIL",
  "BORDERLINE",
  "cannot_verify",
];

/** Attention list, newest first (consumers may slice for display). */
export function attention(records: AnalysisRecord[]): AnalysisRecord[] {
  return byNewest(
    records.filter((r) => ATTENTION_VERDICTS.includes(r.summary.verdict))
  );
}

/**
 * General-mode attention (spec 002): records that produced no nutrition
 * numbers at all — the honest "look again" list when there is no verdict.
 * Newest first, like every selector here.
 */
export function unmeasured(records: AnalysisRecord[]): AnalysisRecord[] {
  return byNewest(
    records.filter((r) => r.summary.grams == null && r.summary.kcal == null)
  );
}

/**
 * Per-record share of the Daily goal (General mode). Shares are computed
 * client-side from the stored summary means — a goal edit re-renders
 * history without any re-analysis (spec 002 user story 23). Null whenever
 * the meal or the goal lacks the nutrient; never an invented number.
 */
export function sharesOfGoal(
  record: AnalysisRecord,
  goal: { kcal: number | null; proteinG: number | null }
): { kcal: number | null; protein: number | null } {
  return {
    kcal: shareOfGoal(record.summary.kcal, goal.kcal),
    protein: shareOfGoal(record.summary.protein, goal.proteinG),
  };
}

export interface DayTotal {
  /** localDateKey(createdAt) bucket, e.g. "2026-10-28" */
  date: string;
  kcal: number;
  protein: number;
  meals: number;
}

/**
 * Per-day sums of the stored meal means, for the General-mode dashboard.
 * Input is newest-first by the RecordsState invariant; output days keep
 * that order (newest day first) and never re-sort records.
 */
export function dayTotals(records: AnalysisRecord[]): DayTotal[] {
  const byDay = new Map<string, DayTotal>();
  for (const r of records) {
    const key = localDateKey(r.createdAt);
    if (!key) continue;
    let bucket = byDay.get(key);
    if (!bucket) {
      bucket = { date: key, kcal: 0, protein: 0, meals: 0 };
      byDay.set(key, bucket);
    }
    bucket.meals += 1;
    if (r.summary.kcal != null && Number.isFinite(r.summary.kcal)) {
      bucket.kcal += r.summary.kcal;
    }
    if (r.summary.protein != null && Number.isFinite(r.summary.protein)) {
      bucket.protein += r.summary.protein;
    }
  }
  return [...byDay.values()];
}

/** Wire dish → label: display name, else classification id, else fallback. */
export function dishLabel(
  result: Pick<AnalyzeResult, "dish" | "classification"> | null | undefined,
  fallback = ""
): string {
  return result?.dish?.display_name || result?.classification?.dish || fallback;
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
      dish: dishLabel(r) || null,
      grams: r.portion?.grams ?? null,
      kcal: r.nutrition?.kcal?.mean ?? null,
      protein: r.nutrition?.protein_g?.mean ?? null,
      coverage: r.coverage?.score ?? null,
      confidence: r.classification?.confidence ?? null,
    },
    result: r,
  };
}
