import { useEffect, useRef, useState } from "react";

export const STAGES = [
  "Checking image",
  "Detecting scale",
  "Segmenting food",
  "Identifying dish",
  "Estimating depth",
  "Estimating portion",
  "Calculating nutrition",
  "Evaluating compliance",
];

interface Props {
  running: boolean;
  failed?: boolean;
}

/**
 * Honest staged loading: stages advance on a local timer while the single
 * /analyze request is in flight — nothing is faked from the backend. The
 * final stage only completes when the response actually arrives.
 */
export default function PipelineProgress({ running, failed = false }: Props) {
  const [active, setActive] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!running) return;
    setActive(0);
    timer.current = window.setInterval(() => {
      setActive((i) => (i >= STAGES.length - 1 ? i : i + 1));
    }, 650);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [running]);

  if (!running && !failed) return null;

  const done = !running && !failed;

  return (
    <div className="card card-pad progress-panel" aria-live="polite">
      <div className="card-head">
        <div>
          <h2 className="card-title">
            {failed ? "Analysis failed" : done ? "Analysis complete" : "Analyzing meal"}
          </h2>
          <p className="card-sub">
            {failed
              ? "The request did not complete."
              : done
                ? "All pipeline stages finished."
                : "Photo → verdict in a single pipeline pass."}
          </p>
        </div>
      </div>

      <ol className="steps list-clean">
        {STAGES.map((label, i) => {
          const state = failed
            ? i < active
              ? "done"
              : i === active
                ? "failed"
                : ""
            : done
              ? "done"
              : i < active
                ? "done"
                : i === active
                  ? "active"
                  : "";
          return (
            <li className={`step ${state}`} key={label}>
              <span className="step-dot" aria-hidden="true">
                {state === "done" ? "✓" : state === "failed" ? "✕" : ""}
              </span>
              {label}
              {state === "active" && <span className="step-meta">running…</span>}
              {state === "done" && !done && i === active - 1 && (
                <span className="step-meta">done</span>
              )}
            </li>
          );
        })}
      </ol>

      <p className="progress-note">
        Stages advance locally while the request is in flight; the pipeline is
        complete only when the backend responds. Verdicts are always computed
        server-side.
      </p>
    </div>
  );
}
