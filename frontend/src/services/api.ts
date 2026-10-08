import type {
  AnalyzeResult,
  HealthResponse,
  MenuResponse,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8731";

export const apiBase = API_BASE;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`);
  } catch {
    throw new ApiError(0, "Cannot reach the NutriSense backend.");
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Backend returned ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getMenu(): Promise<MenuResponse> {
  return get<MenuResponse>("/menu");
}

export function getHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/health");
}

export interface AnalyzeParams {
  file: File;
  day: string;
  band: string;
  serving_style?: string;
}

export async function analyze(params: AnalyzeParams): Promise<AnalyzeResult> {
  const fd = new FormData();
  fd.append("file", params.file);
  fd.append("day", params.day);
  fd.append("band", params.band);
  if (params.serving_style) fd.append("serving_style", params.serving_style);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/analyze`, { method: "POST", body: fd });
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
  const data = (await res.json()) as AnalyzeResult;
  if (!data || typeof data.verdict !== "string") {
    throw new ApiError(500, "The backend returned an unexpected response.");
  }
  return data;
}
