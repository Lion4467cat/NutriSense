export default function CaptureForm({ menu, form, setForm, onSubmit, loading }) {
  const days = menu ? Object.keys(menu.days) : [];
  const bands = menu ? Object.keys(menu.bands) : [];
  const styles = menu
    ? menu.capture_fields.serving_style.values
    : ["mixed", "single"];

  const pickFile = (file) => setForm((f) => ({ ...f, file }));

  return (
    <form
      className="card capture"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <p className="eyebrow">Step 1 — capture</p>
      <h2>Plate photo</h2>

      <label
        className={`drop ${form.preview ? "has-preview" : ""}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) pickFile(f);
        }}
      >
        {form.preview ? (
          <img src={form.preview} alt="selected plate" />
        ) : (
          <span>Drop a photo here or tap to capture</span>
        )}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={(e) => pickFile(e.target.files?.[0] || null)}
        />
      </label>

      <div className="fields">
        <label>
          Day
          <select
            value={form.day}
            onChange={(e) => setForm((f) => ({ ...f, day: e.target.value }))}
          >
            {days.map((d) => (
              <option key={d} value={d}>
                {d.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
        <label>
          Class band
          <select
            value={form.band}
            onChange={(e) => setForm((f) => ({ ...f, band: e.target.value }))}
          >
            {bands.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </label>
        <label>
          Serving style
          <select
            value={form.serving_style}
            onChange={(e) =>
              setForm((f) => ({ ...f, serving_style: e.target.value }))
            }
          >
            {styles.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      <button type="submit" disabled={!form.file || loading}>
        {loading ? "Analyzing…" : "Analyze plate"}
      </button>
      <p className="hint">
        Keep the reference card in frame for measured scale. No digital zoom.
      </p>
    </form>
  );
}
