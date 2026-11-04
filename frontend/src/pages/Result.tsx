import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useGoals } from "../context/goals";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { resolveGoal } from "../services/goals";
import VerdictCard from "../result/VerdictCard";
import PolicyNote from "../result/PolicyNote";
import SummaryCards from "../result/SummaryCards";
import WhyVerdict from "../result/WhyVerdict";
import CoveragePanel from "../result/CoveragePanel";
import NutrientIntervals from "../result/NutrientIntervals";
import MeasurementDetails from "../result/MeasurementDetails";
import MethodologyCard from "../result/MethodologyCard";
import CaptureQuality from "../result/CaptureQuality";
import GeneralResult from "../result/GeneralResult";
import { EmptyState } from "../ui/primitives";
import { IconArrowLeft, IconHistory, IconSparkle } from "../ui/Icon";
import { formatDateTime } from "../utils/format";
import { useMenu } from "../context/menu";
import MealCoach from "../result/MealCoach";
import ItemEvidence from "../result/ItemEvidence";
import type { Analysis } from "../types/contract.gen";
import type { AnalyzeResult } from "../types/api";
import MealRegionFigure from "../result/MealRegionFigure";
import { IS_DEMO_MODE } from "../services/mode";

const critiqueRequests = new Set<string>();

function mealStructureLabel(result: AnalyzeResult): string {
  if (result.path_used === "multi_item") {
    const count = result.segmentation?.n_items ?? result.items?.length ?? 0;
    return count > 0
      ? `${count} ${count === 1 ? "food region" : "food regions"} detected`
      : "Food regions could not be separated";
  }
  if (result.segmentation?.n_items === 1) return "1 food region detected";
  return result.portion
    ? "Analyzed as one serving"
    : "Meal structure could not be confirmed";
}

export default function ResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { records, updateRecord, persistenceWarning } = useRecords();
  const { client } = useMenu();
  const { prefs } = usePrefs();
  const { goals } = useGoals();
  const record = records.find((r) => r.id === id);

  useEffect(() => {
    if (!record || record.critiqueStatus !== "pending" || critiqueRequests.has(record.id)) return;
    if (!client.critiqueMeal) {
      updateRecord(record.id, {
        critiqueStatus: "unavailable",
        critiqueError: "Meal critique is unavailable in this backend client.",
      });
      return;
    }
    critiqueRequests.add(record.id);
    client.critiqueMeal(record.result as Analysis)
      .then((critique) => updateRecord(record.id, {
        critiqueStatus: "ready",
        critique,
        critiqueError: null,
      }))
      .catch((error: unknown) => updateRecord(record.id, {
        critiqueStatus: "unavailable",
        critiqueError: error instanceof Error ? error.message : "Meal critique is unavailable.",
      }))
      .finally(() => critiqueRequests.delete(record.id));
  }, [client, record, updateRecord]);

  if (!record) {
    return (
      <div className="page page-result">
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

  const general = (record.mode ?? prefs.mode ?? "school") === "general";
  const r = record.result;

  const retryCritique = () => {
    critiqueRequests.delete(record.id);
    updateRecord(record.id, { critiqueStatus: "pending", critiqueError: null });
  };

  if (general) {
    return (
      <div className="page page-result">
        <div className="page-head">
          <div>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)} style={{ marginLeft: -11, marginBottom: 6 }}>
              <IconArrowLeft size={14} /> Back
            </button>
            <h1 className="page-title">Meal estimate</h1>
            <p className="page-sub">
              {formatDateTime(record.createdAt)} · {mealStructureLabel(r)}. Estimated portions and nutrients are compared with your daily goals. General mode does not include a school compliance verdict.
            </p>
          </div>
          <div className="result-toolbar">
            <Link className="btn btn-secondary btn-sm" to="/analyze">
              <IconSparkle size={14} /> New analysis
            </Link>
          </div>
        </div>
        {persistenceWarning && (
          <div className="banner error" role="alert" style={{ marginBottom: 16 }}>
            This browser could not save the latest analysis or conversation. It may disappear after refresh.
          </div>
        )}

        <div className="result-stack">
          <GeneralResult
            result={r}
            goal={resolveGoal(goals, prefs.profile, prefs.goalOverride)}
            photo={record.photo}
            demo={IS_DEMO_MODE}
            summaryAddon={(
              <MealCoach record={record} client={client} updateRecord={updateRecord} retryCritique={retryCritique} />
            )}
          />
          <ItemEvidence result={r} />
          <MeasurementDetails result={r} />

          <MethodologyCard result={r} />
        </div>
      </div>
    );
  }

  return (
    <div className="page page-result">
      <div className="page-head">
        <div>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate(-1)} style={{ marginLeft: -11, marginBottom: 6 }}>
            <IconArrowLeft size={14} /> Back
          </button>
          <h1 className="page-title">Analysis result</h1>
          <p className="page-sub">
            {formatDateTime(record.createdAt)} · {record.day.toUpperCase()} ·
            band {record.band} · {mealStructureLabel(r)}
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

      {persistenceWarning && (
        <div className="banner error" role="alert" style={{ marginBottom: 16 }}>
          This browser could not save the latest analysis or conversation. It may disappear after refresh.
        </div>
      )}

      <div className="result-stack">
        <section className={`result-overview${record.photo ? " has-photo" : ""}`} aria-label="Meal summary">
          {record.photo && (
            <MealRegionFigure photo={record.photo} items={r.items ?? []} demo={IS_DEMO_MODE} />
          )}
          <div className="result-summary">
            <VerdictCard result={r} />
            <SummaryCards result={r} />
          </div>
        </section>
        <MealCoach record={record} client={client} updateRecord={updateRecord} retryCritique={retryCritique} />

        <div className="dash-grid" style={{ marginBottom: 0 }}>
          <WhyVerdict result={r} />
          <CoveragePanel result={r} />
        </div>

        <NutrientIntervals result={r} />
        <ItemEvidence result={r} />

        <div className="result-capture">
          <CaptureQuality result={r} />
        </div>

        <MeasurementDetails result={r} />

        <MethodologyCard result={r} />
      </div>
    </div>
  );
}
