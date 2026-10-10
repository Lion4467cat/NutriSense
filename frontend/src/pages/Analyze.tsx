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
import { Card, Collapse } from "../ui/primitives";
import { IconCamera, IconUpload } from "../ui/Icon";
import { bandLabel, dayLabel } from "../utils/format";

type Status = "idle" | "loading" | "error";

export default function AnalyzePage() {
  const { menu, apiUp, checkHealth, client } = useMenu();
  const { records, addRecord } = useRecords();
  const { prefs } = usePrefs();
  const navigate = useNavigate();

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
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Analyze a plated meal</h1>
          <p className="page-sub">
            Upload an original photo of the served meal. For the most reliable
            measurement, include the NutriSense reference card beside the vessel.
          </p>
        </div>
        <span className="local-note">
          {records.length > 0
            ? `${records.length} analysis${records.length > 1 ? "es" : ""} stored locally`
            : "Results are stored in this browser"}
        </span>
      </div>

      {apiUp === false && (
        <div className="banner error" style={{ marginBottom: 16 }}>
          <span aria-hidden="true">✕</span>
          <div>
            <strong>NutriSense backend is currently unavailable.</strong>
            Start it with <span className="mono">.venv/bin/uvicorn main:app --port 8731</span>{" "}
            <button className="btn btn-sm btn-secondary" style={{ marginTop: 8 }} onClick={checkHealth}>
              Retry connection
            </button>
          </div>
        </div>
      )}

      <form className="analyze-grid" onSubmit={submit}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card title="Meal photo" sub="JPEG or PNG · original capture, no digital zoom">
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
                <>
                  <span className="dz-icon">
                    <IconUpload size={20} />
                  </span>
                  <span className="dz-title">Drop a photo here or browse</span>
                  <span className="dz-sub">
                    Shoot from above with the whole vessel in frame. Keep the
                    reference card beside the plate for measured
                    scale.
                  </span>
                </>
              )}
            </label>

            <details className="collapse capture-req" style={{ marginTop: 14 }}>
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
                  <li>Digital zoom must be off (EXIF zoom = 1.0)</li>
                  <li>Use the original photo — not a screenshot or edit</li>
                  <li>Entire tray / vessel visible in frame</li>
                  <li>Reference card beside the vessel (required in every photo)</li>
                  <li>Marker clearly visible, not covered by food</li>
                  <li>Min resolution 1280px on the short side</li>
                </ul>
              </div>
            </details>
          </Card>

          <Card title="Analysis details" sub="Match the serving being captured">
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
            </div>

            <label className="field" style={{ marginTop: 14 }}>
              <span className="field-label">
                Student name{" "}
                <span style={{ fontWeight: 500, color: "var(--text-3)" }}>(optional)</span>
              </span>
              <input
                className="input"
                type="text"
                placeholder="e.g. Aarav S."
                value={student}
                onChange={(e) => setStudent(e.target.value)}
                maxLength={60}
                autoComplete="off"
              />
              <span className="field-hint">
                Links this photo to a student record — stored only in this
                browser for the local compliance log.
              </span>
            </label>

            {status === "error" && error && (
              <div className="banner error" style={{ marginTop: 14 }}>
                <span aria-hidden="true">✕</span>
                <div>
                  <strong>Analysis could not be completed</strong>
                  {error}
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 12, marginTop: 16, alignItems: "center" }}>
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={!file || status === "loading" || !day || !band}
              >
                <IconCamera size={16} />
                {status === "loading" ? "Analyzing…" : "Analyze meal"}
              </button>
              {status === "error" && (
                <button type="button" className="btn btn-ghost" onClick={() => setStatus("idle")}>
                  Dismiss
                </button>
              )}
            </div>
          </Card>
        </div>

        <div>
          {status === "loading" ? (
            <PipelineProgress running />
          ) : status === "error" ? (
            <PipelineProgress running={false} failed />
          ) : (
            <Card title="How it works" sub="Photo → verdict, fully traced">
              <ol className="steps list-clean">
                {STAGE_NAMES.map((stage, i) => (
                  <li className="step" key={stage}>
                    <span className="step-dot" aria-hidden="true">
                      {i + 1}
                    </span>
                    {HOW_IT_WORKS[stage]}
                  </li>
                ))}
              </ol>
              <p className="progress-note">
                Every verdict ships with coverage, uncertainty intervals and the
                assumptions behind them — nothing is hidden.
              </p>
            </Card>
          )}
        </div>
      </form>
    </div>
  );
}
