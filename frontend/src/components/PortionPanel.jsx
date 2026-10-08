export default function PortionPanel({ result }) {
  const p = result.portion;
  const n = result.nutrition;
  if (!p) return null;
  return (
    <section className="card portion">
      <p className="eyebrow">Step 3 — portion</p>
      <h2>
        {p.grams} g <span className="unit">· {p.volume_ml} ml</span>
      </h2>

      <div className="chips">
        <span className="chip">{p.base_method.replace("_", " ")}</span>
        <span className={`chip ${p.scale_tier === "measured" ? "good" : ""}`}>
          scale: {p.scale_tier}
        </span>
        <span className="chip">σ ±{Math.round(p.sigma_grams_rel * 100)}%</span>
        <span className="chip">h̄ {p.mean_h_mm} mm</span>
        <span className="chip">{p.area_cm2} cm²</span>
        <span className="chip">ρ {p.density_eff}</span>
      </div>

      {Object.entries(p.components_g).length > 0 && (
        <div className="components">
          {Object.entries(p.components_g).map(([name, g]) => (
            <div className="comp" key={name}>
              <span>{name}</span>
              <div className="comp-track">
                <div
                  className="comp-fill"
                  style={{
                    width: p.grams > 0 ? `${Math.min(100, (g / p.grams) * 100)}%` : "0%",
                  }}
                />
              </div>
              <b>{g} g</b>
            </div>
          ))}
        </div>
      )}

      {p.flags?.length > 0 && (
        <p className="warn-line">⚠ flags: {p.flags.join(", ")}</p>
      )}

      {n && (
        <div className="mc-summary">
          <div>
            <b>{n.kcal.mean.toFixed(0)}</b>
            <span>kcal (90%: {n.kcal.interval_90[0].toFixed(0)}–
              {n.kcal.interval_90[1].toFixed(0)})</span>
          </div>
          <div>
            <b>{n.protein_g.mean.toFixed(1)} g</b>
            <span>protein (90%: {n.protein_g.interval_90[0].toFixed(1)}–
              {n.protein_g.interval_90[1].toFixed(1)})</span>
          </div>
          <div>
            <b>{n.n}</b>
            <span>MC samples · seed {n.seed}</span>
          </div>
        </div>
      )}
    </section>
  );
}
