import { motion } from "framer-motion";

interface Props {
  running: boolean;
  failed?: boolean;
  demo?: boolean;
}

/** The live API does not stream stage events, so its progress stays indeterminate. */
export default function PipelineProgress({ running, failed = false, demo = false }: Props) {
  if (!running && !failed) return null;

  return (
    <motion.div
      className="card card-pad progress-panel"
      role="status"
      aria-live="polite"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="card-head">
        <div>
          <h2 className="card-title">
            {failed ? "Analysis failed" : demo ? "Preparing demo result" : "Analyzing meal"}
          </h2>
          <p className="card-sub">
            {failed
              ? "The request did not complete. Review the message and retry."
              : demo
                ? "Loading the fixed sample response."
                : "The analysis request is in progress."}
          </p>
        </div>
        {running && <span className="progress-pulse" aria-hidden="true" />}
      </div>

      {running && <div className="progress-track" aria-hidden="true"><span /></div>}

      <p className="progress-note">
        {failed
          ? "Your selected photo stays on this page so you can correct the issue and try again."
          : demo
            ? "Demo mode does not inspect the uploaded pixels or run inference models."
            : "Detailed stage progress is not streamed by the current API; results appear when the server responds."}
      </p>
    </motion.div>
  );
}
