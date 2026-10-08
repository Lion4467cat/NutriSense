import type { AnalyzeResult } from  "../types/api";
import { Card } from  "../ui/primitives";

function iconFor(reason: string): "good" | "bad" | "info" {
  const r = reason.toLowerCase();
  if (
    r.includes("fail zone") ||
    r.includes("below minimum") ||
    r.includes("<= 0.1") ||
    r.includes("< 0.9") ||
    r.includes("unrecognized") ||
    r.includes("failed") ||
    r.includes("unknown ")
  )
    return "bad";
  if (r.includes("all mandatory nutrients")) return "good";
  return "info";
}

export default function WhyVerdict({ result }: { result: AnalyzeResult }) {
  const reasons = result.reasons || [];
  return (
    <Card title="Why this verdict?" sub="Straight from the backend's compliance engine.">
      {reasons.length === 0 ? (
        <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
          No reasons were returned for this analysis.
        </p>
      ) : (
        <ul className="list-clean reason-list">
          {reasons.map((r, i) => (
            <li className="reason-item" key={i}>
              <span className={`r-ico ${iconFor(r)}`} aria-hidden="true">
                {iconFor(r) === "good" ? "✓" : iconFor(r) === "bad" ? "✕" : "i"}
              </span>
              <span>{r}</span>
            </li>
          ))}
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
