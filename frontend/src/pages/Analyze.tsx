import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
import { useMealCapture } from "../analysis/useMealCapture";
import { EASE } from "../ui/motion";

export default function AnalyzePage() {
  const { menu, apiUp, checkHealth, client } = useMenu();
  const { records, addRecord } = useRecords();
  const { prefs } = usePrefs();
  const navigate = useNavigate();

  // General mode (ADR 0003): day/band/student are school capture fields —
  // /analyze is mode-agnostic, so General still sends served defaults.
  const general = (prefs.mode ?? "school") === "general";

  const capture = useMealCapture();
  const { file, preview, dragging, error } = capture;
  const status = capture.phase === "submitting"
    ? "loading"
    : capture.phase === "failed"
      ? "error"
      : "idle";
  const [day, setDay] = useState("");
  const [band, setBand] = useState("");
  const [student, setStudent] = useState("");
  const days = menu ? Object.keys(menu.days) : [];
  const bands = menu ? Object.keys(menu.bands) : [];

  useEffect(() => {
    if (!menu) return;
    setDay((d) => d || prefs.defaultDay || days[0] || "");
    setBand((b) => b || prefs.defaultBand || bands[0] || "");
  }, [menu]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const submittedFile = capture.begin();
    if (!submittedFile) return;
    try {
      const result = await client.analyze({
        file: submittedFile,
        day,
        band,
        mode: general ? "general" : "school",
      });
      const thumb = await fileToThumbnail(submittedFile);
      const record = makeRecord({
        day,
        band,
        mode: general ? "general" : "school",
        student: student.trim() ? { name: student.trim() } : null,
        photo: thumb,
        result,
      });
      addRecord(record);
      capture.complete();
      navigate(`/result/${record.id}`);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.status === 0
            ? "Cannot reach the NutriSense backend. Start the API and retry."
            : err.message
          : "Something went wrong while analyzing this photo.";
      capture.fail(msg);
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
              : "Capture the full meal to estimate energy and protein against school standards, then review practical suggestions."}
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
            <span className="photo-format">JPG · PNG · 12 MB max</span>
          </div>
          <label
              className={`dropzone${dragging ? " dragging" : ""}${preview ? " has-image" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                capture.setDragging(true);
              }}
              onDragLeave={() => capture.setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                capture.setDragging(false);
                capture.selectFile(e.dataTransfer.files?.[0]);
              }}
            >
              <input
                type="file"
                accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                capture="environment"
                disabled={status === "loading"}
                onChange={(e) => {
                  capture.selectFile(e.target.files?.[0]);
                  e.currentTarget.value = "";
                }}
                aria-label="Upload meal photo"
              />
              <AnimatePresence mode="wait" initial={false}>
              {preview ? (
                <motion.span key={preview} className="photo-preview-state" initial={{ opacity: 0, scale: 0.985 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.99 }} transition={{ duration: 0.2, ease: EASE }}>
                  <img src={preview} alt="Selected meal" />
                  <span className="replace-chip">Tap to replace</span>
                </motion.span>
              ) : (
                <motion.span key="empty-upload" className="dropzone-empty" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -3 }} transition={{ duration: 0.18, ease: EASE }}>
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
                </motion.span>
              )}
              </AnimatePresence>
          </label>
          {file && (
            <div className="selected-photo-meta">
              <span title={file.name}>{file.name} · {Math.max(1, Math.round(file.size / 1024))} KB</span>
              <button type="button" className="btn btn-ghost btn-sm" disabled={status === "loading"} onClick={capture.clear}>
                Remove photo
              </button>
            </div>
          )}

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
                  <li>Keep digital zoom off. If the photo has no zoom metadata, NutriSense can identify the meal but will withhold the school-standard verdict.</li>
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
          <div className="setup-head"><span className="workspace-index">02</span><div><h2>Meal details</h2><p>{general ? "Your meal structure is identified from the photo." : "Match the meal to its school service."}</p></div></div>
          <div className="setup-fields">
            {!general && (
              <div className="field-row">
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
              </div>
            )}
            <p className="field-hint" role="status">
              NutriSense checks for one or several food regions and chooses the analysis path automatically.
            </p>

            {!general && (
              <label className="field student-field">
                <span className="field-label">Student <span className="optional-label">OPTIONAL</span></span>
                <input className="input" type="text" placeholder="Name for local record" value={student} onChange={(e) => setStudent(e.target.value)} maxLength={60} autoComplete="off" />
                <span className="field-hint">Stored only in this browser.</span>
              </label>
            )}

            {status === "error" && error && (
              <div className="banner error" role="alert" style={{ marginTop: 14 }}>
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
                  !file || status === "error" ||
                  status === "loading" ||
                  (general ? !menu : !day || !band)
                }
              >
                <IconCamera size={16} />
                {status === "loading" ? (client.demo ? "Preparing demo result…" : "Reading your meal…") : "Analyze this meal"}
              </button>
              {status === "error" && (
                <button type="button" className="btn btn-ghost" onClick={capture.dismissError}>
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
          <p className="privacy-note">{records.length > 0 ? `${records.length} previous ${records.length === 1 ? "analysis" : "analyses"} saved locally` : "Your meal history stays on this device"}</p>
        </aside>

        <div className="analysis-progress">
          {status === "loading" ? (
            <PipelineProgress running demo={client.demo} />
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
