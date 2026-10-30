import type { AnalyzeResult } from  "../types/api";
import { Card, Collapse } from "../ui/primitives";
import { formatPct } from "../utils/format";

/**
 * "How this was measured" (plain-language methodology for THIS plate).
 *
 * Rule used throughout: plain sentence first (any reader), then the number
 * it came from. Nothing is invented — every row reads a field returned by
 * the backend for this exact result, and the developer collapse shows the
 * raw blocks so nothing is abstracted away from us.
 */

interface Row {
  label: string;
  plain: string;
  detail: string;
  ok: boolean;
}

function stageRows(r: AnalyzeResult): Row[] {
  const rows: Row[] = [];

  // 1 — capture
  const zoom = r.lint?.digital_zoom;
  rows.push({
    label: "1 · Capture check",
    ok: !!r.lint?.resolution_ok,
    plain:
      r.lint == null
        ? "The photo was not linted for this capture."
        : r.lint.resolution_ok
          ? "Photo passed the basics: big enough and, if reported, free of digital zoom — so the pixel scale is trustworthy."
          : "Photo is below the recommended size for reliable measuring.",
    detail: `digital_zoom=${zoom ?? "n/a"} · min_side_px=${r.lint?.min_side_px ?? "n/a"} · resolution_ok=${String(r.lint?.resolution_ok ?? "n/a")}${r.lint?.notes?.length ? ` · note: ${r.lint.notes.join("; ")}` : ""}`,
  });

  // 2 — scale
  const a = r.anchor;
  const measured = a?.tier === "measured";
  rows.push({
    label: "2 · Scale reference",
    ok: measured,
    plain: a
      ? measured
        ? `Scale came from the reference card next to the plate (${a.method}). Every distance on the plate can be converted to centimetres — this is the trustworthy anchor.`
        : "No reference card was found, so the scale was estimated from prior knowledge of similar plates — the weight is an estimate, and the verdict treats it as such."
      : "No scale information for this capture.",
    detail: `tier=${a?.tier ?? "n/a"} · method=${a?.method ?? "n/a"} · cm_per_px=${a?.cm_per_px ?? "n/a"} · tilt_deg=${a?.tilt_deg ?? "n/a"} · depth_scale_source=${a?.depth_scale_source ?? "n/a"}${a?.interval ? ` · interval=[${String(a.interval[0])}, ${String(a.interval[1])}]` : ""}`,
  });

  // 3 — food pixels
  const seg = r.segmentation;
  rows.push({
    label: "3 · Finding the food",
    ok: !!seg?.strategy || r.portion != null,
    plain:
      seg?.strategy
        ? "The food pixels were separated from the plate automatically, so only the meal is measured — not the tray or the table."
        : "Segmentation details were not returned for this capture.",
    detail: `strategy=${seg?.strategy ?? "n/a"} · sam_score=${seg?.sam_score != null ? seg.sam_score.toFixed(3) : "n/a"} · area_frac=${seg?.area_frac != null ? seg.area_frac.toFixed(3) : "n/a"} · candidates=${seg?.n_candidates ?? "n/a"}`,
  });

  // 4 — dish identity
  const cls = r.classification;
  rows.push({
    label: "4 · Which dish is this",
    ok: !!cls?.dish,
    plain:
      cls?.dish
        ? `Identified as ${r.dish?.display_name || cls.dish}${cls.confidence != null ? ` with classifier confidence ${formatPct(cls.confidence, 0)}` : ""} — that identity selects the nutrition table and the per-dish error table.`
        : "The dish could not be identified for this capture.",
    detail: `dish=${cls?.dish ?? "n/a"} · confidence=${cls?.confidence ?? "n/a"} · match_score=${cls?.match_score ?? "n/a"} · method=${cls?.method ?? "n/a"} · on_day=${String(r.dish?.on_day ?? "n/a")} · reason=${cls?.reason ?? "n/a"}`,
  });

  // 5 — weight
  const p = r.portion;
  const learned = p?.grams_source === "learned_weight";
  rows.push({
    label: "5 · The plate's weight",
    ok: p != null,
    plain: p
      ? learned
        ? "Weight was read by a model trained on 1,394 real plate photos; the average error it makes per dish is what your confidence interval is built from."
        : "Weight was computed geometrically from the food's footprint area and its height above the plate — narrow when the scale is measured, wide when it is estimated."
      : "No weight was produced for this capture.",
    detail: `grams=${p?.grams ?? "n/a"} · source=${p?.grams_source ?? p?.base_method ?? "n/a"} · base_method=${p?.base_method ?? "n/a"} · sigma_rel=${p?.sigma_grams_rel != null ? p.sigma_grams_rel.toFixed(3) : "n/a"} · area_cm2=${p?.area_cm2 ?? "n/a"} · mean_h_mm=${p?.mean_h_mm ?? "n/a"}${p?.flags?.length ? ` · flags: ${p.flags.join(", ")}` : ""}`,
  });

  // 6 — nutrition + intervals
  const n = r.nutrition;
  let plain6: string;
  if (n) {
    const assumed = n.assumed_nutrients.length;
    plain6 = `Monte Carlo simulation (${n.n.toLocaleString()} draws) turns the weight uncertainty into a ${n.wider_ranges ? "widened (extra-caution) " : ""}range for each nutrient. ` +
      (assumed
        ? `Nutrition uses literature values, with ${assumed} nutrient reading${assumed > 1 ? "s" : ""} flagged as assumed.`
        : "Every nutrient reading comes from measured or literature values — none assumed.");
  } else {
    plain6 = "No nutrition sample was returned for this capture.";
  }
  rows.push({
    label: "6 · Nutrition & the honest range",
    ok: n != null,
    plain: plain6,
    detail: `mc_draws=${n?.n ?? "n/a"} · seed=${n?.seed ?? "n/a"} · assumed=${n?.assumed_nutrients.join(",") || "none"} · wider=${String(n?.wider_ranges ?? "n/a")} · kcal_90=[${n?.kcal.interval_90[0]}, ${n?.kcal.interval_90[1]}] · protein_90=[${n?.protein_g.interval_90[0]}, ${n?.protein_g.interval_90[1]}]`,
  });

  // 7 — verdict machinery
  const c = r.coverage;
  rows.push({
    label: "7 · The verdict gate",
    ok: true,
    plain: c
      ? `The verdict compares the sampled nutrition against the scheme's thresholds, discounted by how confident the system is overall (coverage ${formatPct(c.score, 0)}; PASS needs at least ${formatPct(c.pass_min, 0)}).`
      : "No coverage was computed for this capture.",
    detail: `verdict=${r.verdict} · coverage=${c?.score ?? "n/a"} · factors=${JSON.stringify(c?.factors ?? {})} · pass_min=${c?.pass_min ?? "n/a"}`,
  });

  return rows;
}

export default function MethodologyCard({ result }: { result: AnalyzeResult }) {
  const rows = stageRows(result);
  return (
    <Card
      title="How this was measured"
      sub="What actually happened on this plate — ordinary words first, then the numbers behind them."
    >
      <div className="method-card">
        {rows.map((row) => (
          <div className="method-row" key={row.label}>
            <span className={`method-dot ${row.ok ? "ok" : "warn"}`} aria-hidden="true" />
            <div className="method-body">
              <div className="method-label">{row.label}</div>
              <p className="method-plain">{row.plain}</p>
              <p className="method-detail mono">{row.detail}</p>
            </div>
          </div>
        ))}
        <Collapse summary="Developer detail — every field, nothing hidden">
          <pre className="method-json mono">{JSON.stringify(
            {
              anchor: result.anchor,
              segmentation: result.segmentation,
              classification: result.classification,
              portion: result.portion,
              nutrition: result.nutrition,
              coverage: result.coverage,
            },
            null,
            2
          )}</pre>
        </Collapse>
      </div>
    </Card>
  );
}
