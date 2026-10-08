import type { AnalyzeResult } from  "../types/api";
import { verdictMeta } from  "../ui/primitives";
import { formatPct } from  "../utils/format";

export default function VerdictCard({ result }: { result: AnalyzeResult }) {
  const meta = verdictMeta(result.verdict);
  const cov = result.coverage;
  const dish = result.dish;
  const conf = result.classification?.confidence;

  return (
    <section className={`verdict-card ${meta.cls}`} aria-labelledby="verdict-label">
      <span className="verdict-ico" aria-hidden="true">
        {meta.icon}
      </span>
      <div style={{ minWidth: 0 }}>
        <h2 className="verdict-label" id="verdict-label">
          {meta.label}
        </h2>
        <p className="verdict-msg">{result.reasons?.[0] || meta.blurb}</p>
        <div className="verdict-meta">
          {dish && (
            <span className="tag">
              {dish.display_name || dish.id}
              {dish.on_day === false ? " · off-menu" : ""}
            </span>
          )}
          {dish && <span className="tag">{dish.day?.toUpperCase()}</span>}
          {dish && <span className="tag">band {dish.band}</span>}
          {conf != null && <span className="tag">match {formatPct(conf, 0)}</span>}
          {result.anchor && (
            <span className="tag">
              scale: {result.anchor.tier}
              {result.anchor.depth_scale_source && result.anchor.depth_scale_source !== "none"
                ? ` · calibrated`
                : ""}
            </span>
          )}
        </div>
      </div>

      {cov && (
        <div className="verdict-coverage">
          <div className="cap">Coverage</div>
          <div className="big">{formatPct(cov.score, 0)}</div>
        </div>
      )}
    </section>
  );
}
