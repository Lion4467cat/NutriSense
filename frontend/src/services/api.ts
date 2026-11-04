import type { Analysis } from "../types/contract.gen";
import type {
  GoalsResponse,
  HealthResponse,
  MenuResponse,
} from "../types/api";
import {
  analysisSchema,
  goalsSchema,
  healthSchema,
  menuSchema,
} from "../types/contract.gen";
import { mealCritiqueSchema, parseChatReply, type MealCritique, type MealChatMessage } from "../types/mealCoach";

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
  mode?: "school" | "general";
  serving_style?: string;
}

export interface ApiClient {
  readonly base: string;
  /** True when responses come from the local fixed-sample demo adapter. */
  readonly demo?: boolean;
  getMenu(): Promise<MenuResponse>;
  getGoals(): Promise<GoalsResponse>;
  getHealth(): Promise<HealthResponse>;
  /** Fresh wire responses are full Analysis; stored records use Partial. */
  analyze(params: AnalyzeParams): Promise<Analysis>;
  critiqueMeal?(analysis: Analysis): Promise<MealCritique>;
  chatAboutMeal?(analysis: Analysis, history: MealChatMessage[], message: string): Promise<string>;
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

  async function request(path: string, init: RequestInit, timeoutMs: number): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(`${base}${path}`, { ...init, signal: controller.signal });
    } catch {
      if (controller.signal.aborted) {
        throw new ApiError(408, "The request took too long. Please retry.");
      }
      throw new ApiError(0, "Cannot reach the NutriSense backend.");
    } finally {
      clearTimeout(timer);
    }
  }

  async function postJson<T>(path: string, body: unknown, decode: (value: unknown) => T): Promise<T> {
    const res = await request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }, 120_000);
    if (!res.ok) {
      let detail = `Backend returned ${res.status}.`;
      try {
        const payload = await res.json();
        if (payload?.detail) detail = String(payload.detail);
      } catch {
        /* Keep the status-based message. */
      }
      throw new ApiError(res.status, detail);
    }
    return decode(await res.json());
  }

  const decodeCritique = (value: unknown): MealCritique => {
    const parsed = mealCritiqueSchema.safeParse(value);
    if (!parsed.success) throw new ApiError(500, "The backend returned an unexpected critique.");
    return parsed.data;
  };

  const decodeReply = (value: unknown): string => {
    const reply = parseChatReply(value);
    if (reply === null) throw new ApiError(500, "The backend returned an unexpected chat response.");
    return reply;
  };

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
    if (params.mode) fd.append("mode", params.mode);
    if (params.serving_style) fd.append("serving_style", params.serving_style);

    let res: Response;
    try {
      res = await request("/analyze", { method: "POST", body: fd }, 240_000);
    } catch (err) {
      if (err instanceof ApiError) throw err;
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
    demo: false,
    getMenu: () => getJson("/menu", menuSchema),
    getGoals: () => getJson("/goals", goalsSchema),
    getHealth: () => getJson("/health", healthSchema),
    analyze,
    critiqueMeal: (analysis) => postJson("/meal-critique", { analysis }, decodeCritique),
    chatAboutMeal: (analysis, history, message) => postJson(
      "/meal-chat",
      { analysis, history: history.map(({ role, content }) => ({ role, content })), message },
      decodeReply,
    ),
  };
}
