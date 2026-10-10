import type { Analysis } from "../types/contract.gen";
import type {
  HealthResponse,
  MenuResponse,
} from "../types/api";
import { analysisSchema, healthSchema, menuSchema } from "../types/contract.gen";

export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8731";

/** Config for display/links only — IO goes through a created client. */
export const apiBase = API_BASE;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export interface AnalyzeParams {
  file: File;
  day: string;
  band: string;
  serving_style?: string;
}

export interface ApiClient {
  readonly base: string;
  getMenu(): Promise<MenuResponse>;
  getHealth(): Promise<HealthResponse>;
  /** Fresh wire responses are full Analysis; stored records use Partial. */
  analyze(params: AnalyzeParams): Promise<Analysis>;
}

/** Structural decoder: anything with safeParse (the generated Zod schemas). */
type Decoder<T> = {
  safeParse(data: unknown):
    | { success: true; data: T }
    | { success: false };
};

function decodeWith<T>(dec: Decoder<T>, data: unknown): T {
  const parsed = dec.safeParse(data);
  if (!parsed.success) {
    // contract check: drift in the wire fails here, never renders garbage
    throw new ApiError(500, "The backend returned an unexpected response.");
  }
  return parsed.data;
}

/**
 * Injected IO seam: base URL and fetch are supplied by the composition root
 * (main.tsx builds the real client; tests build stubs).
 */
export function createClient(opts: {
  base: string;
  fetch: typeof globalThis.fetch;
}): ApiClient {
  const { base, fetch } = opts;

  async function getJson<T>(path: string, dec: Decoder<T>): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${base}${path}`);
    } catch {
      throw new ApiError(0, "Cannot reach the NutriSense backend.");
    }
    if (!res.ok) {
      throw new ApiError(res.status, `Backend returned ${res.status} on ${path}`);
    }
    return decodeWith(dec, await res.json());
  }

  async function analyze(params: AnalyzeParams): Promise<Analysis> {
    const fd = new FormData();
    fd.append("file", params.file);
    fd.append("day", params.day);
    fd.append("band", params.band);
    if (params.serving_style) fd.append("serving_style", params.serving_style);

    let res: Response;
    try {
      res = await fetch(`${base}/analyze`, { method: "POST", body: fd });
    } catch {
      throw new ApiError(0, "Cannot reach the NutriSense backend.");
    }
    if (!res.ok) {
      let detail = `Backend returned ${res.status}.`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        /* keep default message */
      }
      throw new ApiError(res.status, detail);
    }
    const data: unknown = await res.json();
    return decodeWith(analysisSchema, data);
  }

  return {
    base,
    getMenu: () => getJson("/menu", menuSchema),
    getHealth: () => getJson("/health", healthSchema),
    analyze,
  };
}
