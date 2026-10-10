import type { AnalyzeResult } from  "../types/api";
import { Card, Collapse } from  "../ui/primitives";
import { formatNum, formatPct } from  "../utils/format";

function KV({ k, v, sub }: { k: string; v: React.ReactNode; sub?: string }) {
  return (
    <div className="kv">
      <div className="k">{k}</div>
      <div className="v">
        {v}
        {sub && <div className="sub">{sub}</div>}
      </div>
    </div>
  );
}

export default function MeasurementDetails({ result }: { result: AnalyzeResult }) {
  const a = result.anchor;
  const c = result.classification;
  const p = result.portion;
  const seg = result.segmentation;
  const mv = result.model_versions || {};
  const assumptions = result.assumptions || [];

  return (
    <Collapse
      summary="Measurement details"
      meta={
        assumptions.length > 0
          ? `${assumptions.length} assumption${assumptions.length > 1 ? "s" : ""}`
          : undefined
      }
    >
      <div className="detail-cols">
        <div className="detail-col">
          <h4>Scale</h4>
          <div className="kv-grid">
            <KV k="Tier" v={a ? a.tier : "—"} />
            <KV k="Method" v={a ? a.method : "—"} />
            <KV
              k="Resolution"
              v={a?.cm_per_px != null ? `${a.cm_per_px.toFixed(4)} cm/px` : "—"}
            />
            <KV k="Tilt" v={a?.tilt_deg != null ? `${a.tilt_deg.toFixed(1)}°` : "—"} />
            <KV
              k="Depth scale"
              v={a?.depth_scale_factor != null ? `×${a.depth_scale_factor}` : "—"}
              sub={a?.depth_scale_source ?? "—"}
            />
            <KV k="Reason" v={a?.reason || "—"} />
          </div>
        </div>

        <div className="detail-col">
          <h4>Classification</h4>
          <div className="kv-grid">
            <KV k="Dish" v={c?.dish || "—"} />
            <KV
              k="Confidence"
              v={c?.confidence != null ? formatPct(c.confidence, 0) : "—"}
            />
            <KV k="Method" v={c?.method || "—"} />
            <KV
              k="Gallery match"
              v={c?.match_score != null ? c.match_score.toFixed(3) : "—"}
            />
            <KV k="Segment" v={seg?.strategy || "—"} />
            <KV
              k="Mask area"
              v={
                seg?.area_frac != null ? `${(seg.area_frac * 100).toFixed(2)}%` : "—"
              }
              sub={seg?.sam_score != null ? `SAM score ${seg.sam_score.toFixed(2)}` : undefined}
            />
          </div>
        </div>

        <div className="detail-col">
          <h4>Portion</h4>
          <div className="kv-grid">
            <KV k="Grams" v={p ? `${formatNum(p.grams, 1)} g` : "—"} />
            <KV k="Volume" v={p ? `${formatNum(p.volume_ml, 0)} ml` : "—"} />
            <KV k="Base method" v={p ? p.base_method.replace(/_/g, " ") : "—"} />
            <KV
              k="Uncertainty"
              v={p ? `±${Math.round(p.sigma_grams_rel * 100)}%` : "—"}
              sub="relative σ on grams"
            />
            <KV k="Height" v={p ? `${formatNum(p.mean_h_mm, 1)} mm` : "—"} />
            <KV k="Footprint" v={p ? `${formatNum(p.area_cm2, 1)} cm²` : "—"} />
          </div>
          {p && p.flags.length > 0 && (
            <div className="chip-row" style={{ marginTop: 10 }}>
              {p.flags.map((f) => (
                <span className="tag" key={f}>
                  ⚠ {f.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}
          {p && Object.keys(p.components_g).length > 0 && (
            <div className="chip-row" style={{ marginTop: 10 }}>
              {Object.entries(p.components_g).map(([name, g]) => (
                <span className="tag" key={name}>
                  {name} {g} g
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="detail-col">
          <h4>Models</h4>
          <div className="kv-grid">
            {Object.entries(mv).map(([k, v]) => (
              <KV key={k} k={k} v={<span className="mono">{v}</span>} />
            ))}
            {Object.keys(mv).length === 0 && <KV k="Models" v="—" />}
            <KV
              k="Monte Carlo"
              v={result.nutrition ? `${result.nutrition.n} samples` : "—"}
              sub={result.nutrition ? `seed ${result.nutrition.seed}` : undefined}
            />
          </div>
        </div>
      </div>

      <hr className="divider" />

      <h4 style={{ fontSize: "var(--fs-xs)", textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-3)", marginBottom: 9 }}>
        Assumptions in play
      </h4>
      {assumptions.length === 0 ? (
        <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
          No assumptions were flagged for this analysis.
        </p>
      ) : (
        <ul className="list-clean assumption-list">
          {assumptions.map((x, i) => (
            <li key={i}>{x}</li>
          ))}
        </ul>
      )}
    </Collapse>
  );
}
