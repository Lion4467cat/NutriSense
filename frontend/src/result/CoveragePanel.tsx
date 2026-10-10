import type { AnalyzeResult } from  "../types/api";
import { FALLBACK_POLICY } from  "../types/api";
import { Card } from  "../ui/primitives";
import { formatPct } from  "../utils/format";

const FACTOR_LABELS: Record<string, string> = {
  anchor_prior: "Prior-tier scale",
  base_table_prior: "Base estimation prior",
  quality_degraded: "Capture quality",
  depth_uncalibrated: "Depth uncalibrated",
};

export default function CoveragePanel({ result }: { result: AnalyzeResult }) {
  const cov = result.coverage;
  const tier = result.anchor?.tier;
  const policy = result.policy ?? FALLBACK_POLICY;

  return (
    <Card
      title="Measurement confidence"
      sub="Coverage reflects how much of the measurement pipeline is supported by reliable evidence."
    >
      {!cov ? (
        <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
          Coverage was not computed — the pipeline exited before verdict
          assessment.
        </p>
      ) : (
        <>
          <div className="cov-score-row">
            <span className="cov-big">{formatPct(cov.score, 0)}</span>
            <span className="muted" style={{ fontSize: "var(--fs-sm)" }}>
              overall coverage
            </span>
          </div>

          <div
            className="cov-track"
            role="img"
            aria-label={`Coverage ${formatPct(cov.score, 0)}, pass gate ${formatPct(
              cov.pass_min,
              0
            )}, fail gate ${formatPct(cov.fail_min, 0)}`}
          >
            <div className="cov-fill" style={{ width: formatPct(cov.score, 2) }} />
            <div
              className="cov-tick"
              data-gate="pass"
              style={{ left: formatPct(cov.pass_min, 2) }}
              data-label={`pass ≥ ${formatPct(cov.pass_min, 0)}`}
            />
            <div
              className="cov-tick"
              data-gate="fail"
              style={{ left: formatPct(cov.fail_min, 2) }}
              data-label={`fail ≥ ${formatPct(cov.fail_min, 0)}`}
            />
          </div>

          <div className="cov-factors">
            {Object.entries(cov.factors || {}).map(([k, v]) => (
              <span className="factor-chip" key={k} title={k}>
                {FACTOR_LABELS[k] || k} × {Number(v).toFixed(2)}
              </span>
            ))}
            {Object.keys(cov.factors || {}).length === 0 && (
              <span className="factor-chip">no degradations ×1.00</span>
            )}
          </div>

          {tier === "prior" && (
            <div className="banner warn" style={{ marginTop: 16 }}>
              <span aria-hidden="true">!</span>
              <div>
                <strong>Prior-tier measurement in use</strong>
                No card or coin was detected, so scale comes from size priors.
                Coverage is capped at {policy.anchor_prior_cap} and this tier can never issue
                PASS/FAIL — verdict is advisory until a reference marker is
                captured.
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
