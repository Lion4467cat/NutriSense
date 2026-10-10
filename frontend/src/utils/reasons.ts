import type { Reason } from "../types/api";

/**
 * Reasons are {kind, text} objects on the wire (engine.contract). Records
 * saved before the contract carried plain strings — normalise both so every
 * consumer can render `reason.text` without crashing.
 */
export function toReasons(raw: unknown): Reason[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((r): Reason => {
    if (typeof r === "string") return { kind: "legacy", text: r };
    if (r && typeof r === "object") {
      const o = r as Partial<Reason>;
      if (typeof o.text === "string") {
        return { kind: typeof o.kind === "string" ? o.kind : "legacy", text: o.text };
      }
    }
    return { kind: "legacy", text: String(r) };
  });
}

export function firstReasonText(raw: unknown): string | undefined {
  return toReasons(raw)[0]?.text;
}
