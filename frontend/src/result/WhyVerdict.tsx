import type { AnalyzeResult } from "../types/api";
import { Card } from "../ui/primitives";
import { reasonTone } from "./verdicts";
import { toReasons } from "../utils/reasons";

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
            const ico = reasonTone(r, result.verdict);
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
