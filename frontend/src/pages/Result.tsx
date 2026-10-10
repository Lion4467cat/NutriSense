import { Link, useNavigate, useParams } from "react-router-dom";
import { useApp } from "../context/AppContext";
import VerdictCard from "../result/VerdictCard";
import PolicyNote from "../result/PolicyNote";
import SummaryCards from "../result/SummaryCards";
import WhyVerdict from "../result/WhyVerdict";
import CoveragePanel from "../result/CoveragePanel";
import NutrientIntervals from "../result/NutrientIntervals";
import MeasurementDetails from "../result/MeasurementDetails";
import CaptureQuality from "../result/CaptureQuality";
import { EmptyState } from "../ui/primitives";
import { IconArrowLeft, IconHistory, IconSparkle } from "../ui/Icon";
import { formatDateTime } from "../utils/format";

export default function ResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { records } = useApp();
  const record = records.find((r) => r.id === id);

  if (!record) {
    return (
      <div className="page">
        <EmptyState
          icon={<IconHistory size={20} />}
          title="Analysis not found"
          action={
            <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
              <button className="btn btn-primary" onClick={() => navigate("/analyze")}>
                Analyze a meal
              </button>
              <Link className="btn btn-secondary" to="/history">
                Open history
              </Link>
            </div>
          }
        >
          This analysis is not in the local store — history lives in this
          browser until the backend adds persistence.
        </EmptyState>
      </div>
    );
  }

  const r = record.result;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)} style={{ marginLeft: -11, marginBottom: 6 }}>
            <IconArrowLeft size={14} /> Back
          </button>
          <h1 className="page-title">Analysis result</h1>
          <p className="page-sub">
            {formatDateTime(record.createdAt)} · {record.day.toUpperCase()} ·
            band {record.band} · {record.serving_style}
            {record.student ? ` · ${record.student.name}` : ""}
          </p>
          <PolicyNote record={record} />
        </div>
        <div className="result-toolbar">
          <Link className="btn btn-secondary btn-sm" to="/analyze">
            <IconSparkle size={14} /> New analysis
          </Link>
        </div>
      </div>

      <div className="result-stack">
        <VerdictCard result={r} />
        <SummaryCards result={r} />

        <div className="dash-grid" style={{ marginBottom: 0 }}>
          <WhyVerdict result={r} />
          <CoveragePanel result={r} />
        </div>

        <NutrientIntervals result={r} />

        <div className="dash-grid" style={{ marginBottom: 0 }}>
          <CaptureQuality result={r} />
          {record.photo && (
            <section className="card card-pad">
              <div className="card-head">
                <div>
                  <h2 className="card-title">Captured photo</h2>
                  <p className="card-sub">Local thumbnail of the original upload</p>
                </div>
              </div>
              <img
                src={record.photo}
                alt="Analyzed meal"
                style={{ borderRadius: "var(--r-md)", border: "1px solid var(--border)" }}
              />
            </section>
          )}
        </div>

        <MeasurementDetails result={r} />
      </div>
    </div>
  );
}
