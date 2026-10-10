import type { AnalyzeResult, Reason } from "../types/api";
import { Card } from "../ui/primitives";
import { toReasons } from "../utils/reasons";

const KIND_ICON: Record<string, "good" | "bad" | "info"> = {
  in_zone: "good",
  below_min: "bad",
  stage_failed: "bad",
  unrecognized: "bad",
  zoom: "bad",
  unknown_day: "bad",
  unknown_band: "bad",
  unreadable: "info",
  out_of_scope: "info",
  coverage_gate: "info",
};

function iconFor(reason: Reason): "good" | "bad" | "info" {
  const known = KIND_ICON[reason.kind];
  if (known) return known;
  if (reason.kind !== "legacy") return "info"; // open vocabulary: default glyph
  // legacy v1 string reasons: keep the old prose heuristics
  const t = reason.text.toLowerCase();
  if (
    t.includes("fail zone") ||
    t.includes("below minimum") ||
    t.includes("<= 0.1") ||
    t.includes("< 0.9") ||
    t.includes("unrecognized") ||
    t.includes("failed") ||
    t.includes("unknown ")
  )
    return "bad";
  if (t.includes("all mandatory nutrients")) return "good";
  return "info";
}

export default function WhyVerdict({ result }: { result: AnalyzeResult }) {
  const reasons = toReasons(result.reasons);
  return (
    <Card title="Why this verdict?" sub="Straight from the backend's compliance engine.">
      {reasons.length === 0 ? (
        <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
          No reasons were returned for this analysis.
        </p>
      ) : (
        <ul className="list-clean reason-list">
          {reasons.map((r, i) => {
            const ico = iconFor(r);
            return (
              <li className="reason-item" key={i}>
                <span className={`r-ico ${ico}`} aria-hidden="true">
                  {ico === "good" ? "✓" : ico === "bad" ? "✕" : "i"}
                </span>
                <span>{r.text}</span>
              </li>
            );
          })}
        </ul>
      )}

      {result.advisory && (
        <div className="banner info" style={{ marginTop: 14 }}>
          <span aria-hidden="true">ℹ</span>
          <div>
            <strong>Salt advisory (informational)</strong>
            {result.advisory.sodium_salt
              ? `Primary ${result.advisory.sodium_salt.primary_g} g / upper ${result.advisory.sodium_salt.upper_g} g. `
              : ""}
            {result.advisory.note || "Salt never affects the verdict."}
          </div>
        </div>
      )}
    </Card>
  );
}
