import type { AnalyzeResult } from "../types/api";
import { formatNum } from "../utils/format";

export default function ItemEvidence({ result }: { result: AnalyzeResult }) {
  const items = result.items ?? [];
  if (!items.length) return null;

  return (
    <section className="card card-pad">
      <div className="card-head">
        <div>
          <h2 className="card-title">Detected food items</h2>
          <p className="card-sub">Per-item evidence used by the meal estimate.</p>
        </div>
        <span className="eyebrow">{items.length} regions</span>
      </div>
      <div className="item-evidence-list">
        {items.map((item, index) => {
          const label = item.dish?.display_name || item.classification?.dish || "Unidentified item";
          return (
            <article className="item-evidence" key={`${label}-${index}`}>
              <div>
                <strong>{label}</strong>
                {item.portion?.grams != null && (
                  <span className="muted"> · {formatNum(item.portion.grams, 1)} g estimated</span>
                )}
              </div>
              <div className="item-evidence-meta">
                {item.bbox && <span>Region {item.bbox.map((n) => Math.round(n)).join(", ")}</span>}
                {item.area_frac != null && <span>{(item.area_frac * 100).toFixed(1)}% mask area</span>}
                {item.sam_score != null && <span>Mask score {item.sam_score.toFixed(2)}</span>}
              </div>
              {item.reason && <p className="meal-coach-caveat">{item.reason.text}</p>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
