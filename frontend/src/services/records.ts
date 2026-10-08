import type { AnalyzeResult, Verdict } from "../types/api";

/**
 * Local analysis store.
 *
 * The backend does not persist analyses today, so the frontend keeps a
 * browser-local history (localStorage) that a future history endpoint can
 * replace — the shape below is the record the UI reads from.
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

const KEY = "nutrisense.records.v1";
const MAX_RECORDS = 200;

export function loadRecords(): AnalysisRecord[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((r) => r && typeof r.id === "string");
  } catch {
    return [];
  }
}

export function saveRecords(records: AnalysisRecord[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(records.slice(0, MAX_RECORDS)));
  } catch {
    /* storage full — drop thumbnails from oldest entries and retry once */
    try {
      const slim = records.slice(0, MAX_RECORDS).map((r, i) =>
        i < records.length - 30 ? { ...r, photo: null } : r
      );
      localStorage.setItem(KEY, JSON.stringify(slim));
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
