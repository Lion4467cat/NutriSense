import type {
  AnalyzeResult,
  HealthResponse,
  MenuResponse,
} from "../types/api";
import { analysisSchema } from "../types/contract.gen";

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
  analyze(params: AnalyzeParams): Promise<AnalyzeResult>;
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

  async function get<T>(path: string): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${base}${path}`);
    } catch {
      throw new ApiError(0, "Cannot reach the NutriSense backend.");
    }
    if (!res.ok) {
      throw new ApiError(res.status, `Backend returned ${res.status} on ${path}`);
    }
    return res.json() as Promise<T>;
  }

  async function analyze(params: AnalyzeParams): Promise<AnalyzeResult> {
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
    // contract check: the wire is validated against the generated Zod schema
    const parsed = analysisSchema.safeParse(data);
    if (!parsed.success) {
      throw new ApiError(500, "The backend returned an unexpected response.");
    }
    return parsed.data;
  }

  return {
    base,
    getMenu: () => get<MenuResponse>("/menu"),
    getHealth: () => get<HealthResponse>("/health"),
    analyze,
  };
}
