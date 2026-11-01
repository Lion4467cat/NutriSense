import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMenu } from "../context/menu";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { ApiError } from "../services/api";
import { makeRecord } from "../services/records";
import { fileToThumbnail } from "../utils/image";
import PipelineProgress from "../analysis/PipelineProgress";
import { HOW_IT_WORKS } from "../analysis/stages";
import { STAGE_NAMES } from "../types/contract.gen";
import { IconCamera, IconUpload } from "../ui/Icon";
import { bandLabel, dayLabel } from "../utils/format";

type Status = "idle" | "loading" | "error";

export default function AnalyzePage() {
  const { menu, apiUp, checkHealth, client } = useMenu();
  const { records, addRecord } = useRecords();
  const { prefs } = usePrefs();
  const navigate = useNavigate();

  // General mode (ADR 0003): day/band/student are school capture fields —
  // /analyze is mode-agnostic, so General still sends served defaults.
  const general = (prefs.mode ?? "school") === "general";

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [day, setDay] = useState("");
  const [band, setBand] = useState("");
  const [style, setStyle] = useState("mixed");
  const [student, setStudent] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const previewRef = useRef<string | null>(null);

  const days = menu ? Object.keys(menu.days) : [];
  const bands = menu ? Object.keys(menu.bands) : [];
  const styles = menu?.capture_fields?.serving_style?.values || ["mixed", "single"];

  useEffect(() => {
    if (!menu) return;
    setDay((d) => d || prefs.defaultDay || days[0] || "");
    setBand((b) => b || prefs.defaultBand || bands[0] || "");
    setStyle((s) => (menu.capture_fields?.serving_style?.values.includes(s) ? s : "mixed"));
  }, [menu]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    if (!file) {
      setPreview(null);
      previewRef.current = null;
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    previewRef.current = url;
    return () => {
      if (previewRef.current === url) {
        URL.revokeObjectURL(url);
        previewRef.current = null;
      }
    };
  }, [file]);

  const pickFile = (f: File | null | undefined) => {
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setError("That file type isn't supported — please choose an image (JPEG or PNG).");
      setStatus("error");
      return;
    }
    setError(null);
    setStatus("idle");
    setFile(f);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || status === "loading") return;
    setStatus("loading");
    setError(null);
    try {
      const result = await client.analyze({ file, day, band, serving_style: style });
      const thumb = await fileToThumbnail(file);
      const record = makeRecord({
        day,
        band,
        serving_style: style,
        mode: general ? "general" : "school",
        student: student.trim() ? { name: student.trim() } : null,
        photo: thumb,
        result,
      });
      addRecord(record);
      navigate(`/result/${record.id}`);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.status === 0
            ? "Cannot reach the NutriSense backend. Start the API and retry."
            : err.message
          : "Something went wrong while analyzing this photo.";
      setError(msg);
      setStatus("error");
      if (err instanceof ApiError && err.status === 0) checkHealth();
    }
  };

  return (
    <div className="page page-analyze">
      <div className="analyze-intro">
        <div className="analyze-intro-copy">
          <span className="eyebrow">Meal studio <span>·</span> A fresh look</span>
          <h1 className="page-title">{general ? <>A clearer look at <em>your plate.</em></> : <>A clearer look at <em>every meal.</em></>}</h1>
          <p className="page-sub">
            {general
              ? "A photo becomes a nutrition estimate, followed by practical ideas for what to add or ease back on."
              : "Capture the full serving to assess nutrition and school meal coverage."}
          </p>
        </div>
        <div className="analyze-intro-note">
          <span className="local-note">{records.length > 0
            ? `${records.length} meal${records.length === 1 ? "" : "s"} in your local history`
            : "Saved to this browser"}</span>
          <span className="intro-step"><b>01</b> Capture <i /> <span>02</span> Review
          </span>
        </div>
      </div>

      {apiUp === false && (
        <div className="connection-note" role="status">
          <span className="connection-dot" aria-hidden="true" />
          <span><strong>Analysis service offline.</strong> Start the API to analyze a meal.</span>
          <button className="connection-retry" onClick={checkHealth}>Retry</button>
        </div>
      )}

      <form className="analyze-grid studio-grid" onSubmit={submit}>
        <section className="photo-workspace" aria-label="Meal photo">
          <div className="workspace-heading">
            <div><span className="workspace-index">01</span><div><h2>Photograph the meal</h2><p>A clear, complete view helps the estimate.</p></div></div>
            <span className="photo-format">JPG · PNG</span>
          </div>
          <label
              className={`dropzone${dragging ? " dragging" : ""}${preview ? " has-image" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pickFile(e.dataTransfer.files?.[0]);
              }}
            >
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={(e) => pickFile(e.target.files?.[0])}
                aria-label="Upload meal photo"
              />
              {preview ? (
                <>
                  <img src={preview} alt="Selected meal" />
                  <span className="replace-chip">Tap to replace</span>
                </>
              ) : (
                <span className="dropzone-empty">
                  <span className="upload-copy">
                    <span className="upload-kicker">Step 1 · Photo</span>
                    <span className="dz-title">Bring your plate into focus.</span>
                    <span className="dz-sub">Drop a photo here, or choose one from your device.</span>
                    <span className="upload-action"><IconUpload size={16} /> Choose a photo</span>
                    <span className="dz-guidance"><IconCamera size={14} /> Shoot from above. Keep the whole vessel in frame.</span>
                  </span>
                  <span className="upload-example">
                    <img src="/plate.jpg" alt="Example of a full meal tray photographed from above" />
                    <span className="example-caption">Example capture <i /> Full tray in frame</span>
                  </span>
                </span>
              )}
          </label>

          <details className="collapse capture-req studio-capture-req">
              <summary>
                Capture requirements
                <svg
                  className="chev"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  aria-hidden="true"
                >
                  <path d="m6 9.5 6 6 6-6" />
                </svg>
              </summary>
              <div className="capture-req" style={{ padding: "0 16px 16px" }}>
                <ul>
                  <li>Turn off digital zoom (EXIF zoom must be 1.0).</li>
                  <li>Use the original image, not a screenshot or an edited copy.</li>
                  <li>Keep the entire tray or vessel in the frame.</li>
                  <li>Place the reference card beside the vessel for a measured scale. Without it, weight is estimated.</li>
                  <li>Keep the reference marker visible and uncovered.</li>
                  <li>Use an image with a shorter side of at least 1,280 pixels.</li>
                </ul>
              </div>
          </details>
        </section>

        <aside className="meal-setup">
          <div className="setup-head"><span className="workspace-index">02</span><div><h2>Tell us a little more</h2><p>{general ? "Choose the serving style for this meal." : "Match the meal to its school service."}</p></div></div>
          <div className="setup-fields">
            <div className="field-row">
              {general ? (
                <label className="field">
                  <span className="field-label">Serving style</span>
                  <select className="select" value={style} onChange={(e) => setStyle(e.target.value)}>
                    {styles.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <>
                  <label className="field">
                    <span className="field-label">Day</span>
                    <select className="select" value={day} onChange={(e) => setDay(e.target.value)}>
                      {days.map((d) => (
                        <option key={d} value={d}>
                          {dayLabel(d)}
                        </option>
                      ))}
                      {!menu && <option value="">—</option>}
                    </select>
                  </label>

                  <label className="field">
                    <span className="field-label">Class band</span>
                    <select className="select" value={band} onChange={(e) => setBand(e.target.value)}>
                      {bands.map((b) => (
                        <option key={b} value={b}>
                          {bandLabel(b)}
                        </option>
                      ))}
                      {!menu && <option value="">—</option>}
                    </select>
                  </label>

                  <label className="field">
                    <span className="field-label">Serving style</span>
                    <select className="select" value={style} onChange={(e) => setStyle(e.target.value)}>
                      {styles.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              )}
            </div>

            {!general && (
              <label className="field student-field">
                <span className="field-label">Student <span className="optional-label">OPTIONAL</span></span>
                <input className="input" type="text" placeholder="Name for local record" value={student} onChange={(e) => setStudent(e.target.value)} maxLength={60} autoComplete="off" />
                <span className="field-hint">Stored only in this browser.</span>
              </label>
            )}

            {status === "error" && error && (
              <div className="banner error" style={{ marginTop: 14 }}>
                <span aria-hidden="true">✕</span>
                <div>
                  <strong>Analysis could not be completed</strong>
                  {error}
                </div>
              </div>
            )}

            {general && <div className="reference-note"><span aria-hidden="true">i</span><p>Reference card improves portion scale. Without it, weight is estimated from the image.</p></div>}
          </div>
          <div className="setup-submit">
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={
                  !file ||
                  status === "loading" ||
                  (general ? !menu : !day || !band)
                }
              >
                <IconCamera size={16} />
                {status === "loading" ? "Reading your meal…" : "Analyze this meal"}
              </button>
              {status === "error" && (
                <button type="button" className="btn btn-ghost" onClick={() => setStatus("idle")}>
                  Dismiss
                </button>
              )}
            </div>
            {general && !menu && (
              <p className="field-hint" style={{ marginTop: 10 }}>
                Waiting for the backend's dish and goal data before this meal
                can be analyzed.
              </p>
            )}
          <p className="privacy-note">{records.length > 0 ? `${records.length} previous analysis${records.length === 1 ? "" : "es"} saved locally` : "Your meal history stays on this device"}</p>
        </aside>

        <div className="analysis-progress">
          {status === "loading" ? (
            <PipelineProgress running />
          ) : status === "error" ? (
            <PipelineProgress running={false} failed />
          ) : (
            <div className="analysis-assurance">
              <span className="assurance-mark">↗</span>
              <p>{general ? "Your estimate includes uncertainty ranges and a meal-level critique." : "Every verdict includes coverage, uncertainty ranges, and the assumptions behind it."}</p>
              <details><summary>How the analysis works</summary><ol className="steps list-clean">{STAGE_NAMES.map((stage, i) => <li className="step" key={stage}><span className="step-dot" aria-hidden="true">{i + 1}</span>{HOW_IT_WORKS[stage]}</li>)}</ol></details>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}
