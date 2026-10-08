const VERDICT_META = {
  PASS: { icon: "✓", label: "PASS", cls: "pass" },
  FAIL: { icon: "✕", label: "FAIL", cls: "fail" },
  BORDERLINE: { icon: "!", label: "BORDERLINE", cls: "warn" },
  cannot_verify: { icon: "?", label: "CANNOT VERIFY", cls: "mute" },
  out_of_scope: { icon: "–", label: "OUT OF SCOPE", cls: "mute" },
};

function CoverageBar({ coverage }) {
  if (!coverage) return null;
  const { score, pass_min, fail_min, factors } = coverage;
  const pct = (v) => `${Math.min(100, Math.max(0, v * 100))}%`;
  return (
    <div className="coverage">
      <div className="coverage-head">
        <span>Coverage</span>
        <b>{score.toFixed(2)}</b>
        <span className="gate">
          pass ≥ {pass_min} · fail ≥ {fail_min}
        </span>
      </div>
      <div className="coverage-track">
        <div className="coverage-fill" style={{ width: pct(score) }} />
        <div className="tick" style={{ left: pct(pass_min) }} />
        <div className="tick hard" style={{ left: pct(fail_min) }} />
      </div>
      {factors && (
        <div className="factors">
          {Object.entries(factors).map(([k, v]) => (
            <span key={k} className="factor">
              {k} × {Number(v).toFixed(2)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function VerdictCard({ result }) {
  const meta = VERDICT_META[result.verdict] || VERDICT_META.cannot_verify;
  const dish = result.dish;
  return (
    <section className={`card verdict ${meta.cls}`}>
      <div className="verdict-top">
        <span className="badge">{meta.icon}</span>
        <div>
          <h2>{meta.label}</h2>
          {dish && (
            <p className="dish-line">
              {dish.display_name || dish.id}
              <span className="muted">
                {" "}
                · {dish.day?.toUpperCase()} · band {dish.band}
                {dish.serving_style ? ` · ${dish.serving_style}` : ""}
              </span>
            </p>
          )}
        </div>
      </div>

      <ul className="reasons">
        {result.reasons?.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>

      {dish && dish.on_day === false && (
        <p className="warn-line">
          ⚠ {dish.display_name || dish.id} is not on this day's official menu.
        </p>
      )}

      <CoverageBar coverage={result.coverage} />

      {result.assumptions?.length > 0 && (
        <details className="assumptions">
          <summary>Assumptions in play ({result.assumptions.length})</summary>
          <ul>
            {result.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}

      {result.advisory && (
        <p className="advisory">
          💧 Salt advisory: {result.advisory.sodium_salt?.primary_g}g primary /
          {result.advisory.sodium_salt?.upper_g}g upper — advisory only, never a
          verdict nutrient.
        </p>
      )}
    </section>
  );
}
