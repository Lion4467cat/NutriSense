const LABELS = { kcal: "Energy", protein_g: "Protein" };
const UNITS = { kcal: "kcal", protein_g: "g" };

function IntervalBar({ nutrientKey, row, p }) {
  const lo = row.interval_90[0];
  const hi = row.interval_90[1];
  const domain = Math.max(hi, row.min) * 1.15;
  const pct = (v) => `${Math.min(100, Math.max(0, (v / domain) * 100))}%`;
  const pClass = p >= 0.9 ? "good" : p <= 0.1 ? "bad" : "warn";
  const unit = UNITS[nutrientKey];
  const fmt = (v) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1));

  return (
    <div className="nutrient">
      <div className="nutrient-head">
        <span className="nutrient-label">{LABELS[nutrientKey]}</span>
        <span className={`p-chip ${pClass}`}>P = {p.toFixed(2)}</span>
      </div>
      <div className="nutrient-track" title={`mean ${fmt(row.mean)} ${unit}`}>
        <div
          className="nutrient-interval"
          style={{ left: pct(lo), width: pct(hi - lo) }}
        />
        <div className="nutrient-mean" style={{ left: pct(row.mean) }} />
        <div className="nutrient-min" style={{ left: pct(row.min) }}>
          <span>min {row.min}</span>
        </div>
      </div>
      <div className="nutrient-foot">
        <span>avg {fmt(row.mean)} {unit}</span>
        <span>90% interval {fmt(lo)}–{fmt(hi)} {unit}</span>
        <span>
          headroom at low:{" "}
          {row.headroom_at_interval_low >= 0 ? "+" : ""}
          {fmt(row.headroom_at_interval_low)} {unit}
        </span>
      </div>
    </div>
  );
}

export default function NutrientBars({ compliance }) {
  if (!compliance || !compliance.nutrients || !compliance.probs)
    return null;
  return (
    <section className="card nutrients">
      <p className="eyebrow">Step 2 — compliance vs band standard</p>
      <h2>Mandatory nutrients</h2>
      {Object.entries(compliance.nutrients).map(([key, row]) => (
        <IntervalBar key={key} nutrientKey={key} row={row} p={compliance.probs[key]} />
      ))}
      <p className="hint">
        Bars show the MC 90% interval against the PM POSHAN band minimum; P is
        P(at or above minimum) from 4000 samples.
      </p>
    </section>
  );
}
