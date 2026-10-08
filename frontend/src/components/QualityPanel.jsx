export default function QualityPanel({ result }) {
  const { lint, anchor, segmentation, classification, model_versions } = result;
  return (
    <section className="card quality">
      <p className="eyebrow">Capture & model diagnostics</p>
      <h2>Quality</h2>

      <div className="qgrid">
        <div>
          <h3>Anchor</h3>
          <p>
            <b>{anchor?.tier || "—"}</b> · {anchor?.method || "—"}
            {anchor?.cm_per_px != null && (
              <>
                {" "}
                · {anchor.cm_per_px.toFixed(4)} cm/px
              </>
            )}
          </p>
          {anchor?.tilt_deg != null && <p>tilt ≈ {anchor.tilt_deg.toFixed(1)}°</p>}
          <p>
            depth scale ×{anchor?.depth_scale_factor ?? "—"} (
            {anchor?.depth_scale_source || "none"})
          </p>
        </div>

        <div>
          <h3>Lint</h3>
          <p>zoom: {lint?.digital_zoom ?? "unknown"}</p>
          <p>
            min side {lint?.min_side_px}px{" "}
            {lint?.resolution_ok ? "✓" : "⚠ below 1280"}
          </p>
          {lint?.notes?.map((note, i) => (
            <p key={i} className="warn-line">
              ⚠ {note}
            </p>
          ))}
        </div>

        <div>
          <h3>Segmentation</h3>
          <p>{segmentation?.strategy || "—"} </p>
          {segmentation?.sam_score != null && (
            <p>SAM score {segmentation.sam_score.toFixed(2)}</p>
          )}
          {segmentation?.area_frac != null && (
            <p>area {Math.round(segmentation.area_frac * 100)}% of frame</p>
          )}
        </div>

        <div>
          <h3>Classification</h3>
          <p>method: {classification?.method || "—"}</p>
          {classification?.confidence != null && (
            <p>confidence {classification.confidence.toFixed(2)}</p>
          )}
          {classification?.match_score != null && (
            <p>gallery match {classification.match_score.toFixed(2)}</p>
          )}
        </div>
      </div>

      {result.nutrition?.assumed_nutrients?.length > 0 && (
        <p className="hint">
          assumed nutrient rows:{" "}
          {result.nutrition.assumed_nutrients.join(", ")}
          {result.nutrition.wider_ranges ? " · wider generic ranges" : ""}
        </p>
      )}

      <div className="versions">
        {Object.entries(model_versions || {}).map(([k, v]) => (
          <span key={k} className="chip">
            {k}: {v}
          </span>
        ))}
      </div>
    </section>
  );
}
