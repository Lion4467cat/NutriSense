import { useEffect, useRef, useState } from "react";
import { analyze, getHealth, getMenu } from "./api";
import CaptureForm from "./components/CaptureForm";
import VerdictCard from "./components/VerdictCard";
import NutrientBars from "./components/NutrientBars";
import PortionPanel from "./components/PortionPanel";
import QualityPanel from "./components/QualityPanel";

const DEFAULT_FORM = { file: null, preview: null, day: "mon", band: "1-5", serving_style: "mixed" };

export default function App() {
  const [menu, setMenu] = useState(null);
  const [apiUp, setApiUp] = useState(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const previewRef = useRef(null);

  useEffect(() => {
    getMenu()
      .then((m) => {
        setMenu(m);
        const firstDay = Object.keys(m.days)[0];
        const firstBand = Object.keys(m.bands)[0];
        setForm((f) => ({ ...f, day: firstDay, band: firstBand }));
      })
      .catch(() => setMenu(null));
    getHealth()
      .then(() => setApiUp(true))
      .catch(() => setApiUp(false));
  }, []);

  useEffect(() => {
    if (form.file) {
      const url = URL.createObjectURL(form.file);
      setForm((f) => ({ ...f, preview: url }));
      previewRef.current = url;
      return () => URL.revokeObjectURL(url);
    }
    setForm((f) => ({ ...f, preview: null }));
  }, [form.file]);

  const submit = async () => {
    if (!form.file) return;
    setStatus("loading");
    setError(null);
    try {
      const out = await analyze(form);
      setResult(out);
      setStatus("done");
    } catch (e) {
      setError(e.message || String(e));
      setStatus("error");
    }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🍱</span>
          <div>
            <h1>NutriSense</h1>
            <p>PM POSHAN plate compliance</p>
          </div>
        </div>
        <span
          className={`api-dot ${apiUp ? "up" : apiUp === false ? "down" : ""}`}
          title={apiUp ? "API connected" : "API unreachable"}
        >
          {apiUp ? "API ok" : apiUp === false ? "API down" : "connecting…"}
        </span>
      </header>

      <main className="grid">
        <CaptureForm
          menu={menu}
          form={form}
          setForm={setForm}
          onSubmit={submit}
          loading={status === "loading"}
        />

        <section className="results" aria-live="polite">
          {status === "idle" && (
            <div className="card placeholder">
              <p className="big">📸</p>
              <p>
                Add a plate photo, pick the day and band, then hit{" "}
                <b>Analyze plate</b>.
              </p>
            </div>
          )}
          {status === "loading" && (
            <div className="card placeholder">
              <div className="spinner" />
              <p>Analyzing — segmenting, measuring, sampling 4000×…</p>
            </div>
          )}
          {status === "error" && (
            <div className="card error">
              <h2>Something went wrong</h2>
              <p>{error}</p>
              <button onClick={() => setStatus("idle")}>Try again</button>
            </div>
          )}
          {status === "done" && result && (
            <>
              <VerdictCard result={result} />
              <NutrientBars compliance={result.compliance} />
              <PortionPanel result={result} />
              <QualityPanel result={result} />
            </>
          )}
        </section>
      </main>

      <footer className="foot">
        verdicts are advisory decision support — PASS/FAIL requires measured
        scale and coverage ≥ 0.85/0.90
      </footer>
    </div>
  );
}
