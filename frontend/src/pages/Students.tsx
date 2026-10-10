import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useRecords } from "../context/records";
import { Card, EmptyState } from "../ui/primitives";
import { VerdictPill } from "../result/VerdictPill";
import { IconArrowLeft, IconUsers } from "../ui/Icon";
import { formatDate, formatNum, formatPct } from "../utils/format";
import type { AnalysisRecord } from "../services/records";

interface Group {
  name: string;
  records: AnalysisRecord[];
  bands: string[];
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || "")
    .join("");
}

function streakClass(v: string): string {
  if (v === "PASS") return "pass";
  if (v === "BORDERLINE") return "warn";
  if (v === "FAIL") return "fail";
  return "neutral";
}

function useGroups(): Group[] {
  const { records } = useRecords();
  return useMemo(() => {
    const map = new Map<string, AnalysisRecord[]>();
    for (const r of records) {
      if (!r.student?.name) continue;
      const list = map.get(r.student.name) || [];
      list.push(r);
      map.set(r.student.name, list);
    }
    return [...map.entries()]
      .map(([name, list]) => {
        const sorted = [...list].sort(
          (a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)
        );
        return {
          name,
          records: sorted,
          bands: [...new Set(sorted.map((r) => r.band))],
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [records]);
}

function StudentList() {
  const navigate = useNavigate();
  const groups = useGroups();

  if (groups.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<IconUsers size={20} />}
          title="No student records yet"
          action={
            <Link className="btn btn-primary" to="/analyze" style={{ marginTop: 6 }}>
              Analyze a meal with a student name
            </Link>
          }
        >
          Add a student name on the Analyze page to map each photo to a child —
          name, class band and pass/fail per date. Records stay in this browser.
        </EmptyState>
      </Card>
    );
  }

  return (
    <div className="student-grid">
      {groups.map((g) => {
        const scored = g.records.filter((r) =>
          ["PASS", "BORDERLINE", "FAIL"].includes(r.summary.verdict)
        );
        const pass = scored.filter((r) => r.summary.verdict === "PASS").length;
        const last6 = g.records.slice(0, 6).reverse();
        return (
          <button
            key={g.name}
            className="student-card"
            onClick={() => navigate(`/students/${encodeURIComponent(g.name)}`)}
          >
            <div className="st-top">
              <span className="avatar" aria-hidden="true">
                {initials(g.name)}
              </span>
              <div style={{ minWidth: 0 }}>
                <div className="st-name">{g.name}</div>
                <div className="st-sub">
                  Classes {g.bands.join(", ")} ·{" "}
                  {g.records.length} meal{g.records.length === 1 ? "" : "s"}
                </div>
              </div>
              <span
                className={`pill ${
                  !scored.length
                    ? "neutral"
                    : pass === scored.length
                      ? "pass"
                      : pass / scored.length >= 0.5
                        ? "warn"
                        : "fail"
                }`}
                style={{ marginLeft: "auto" }}
              >
                {scored.length ? formatPct(pass / scored.length, 0) : "—"}
              </span>
            </div>
            <div className="streak" aria-label="Recent verdicts">
              {last6.map((r) => (
                <span
                  className={`streak-dot ${streakClass(r.summary.verdict)}`}
                  key={r.id}
                  title={`${formatDate(r.createdAt)}: ${r.summary.verdict}`}
                >
                  {r.summary.verdict === "PASS"
                    ? "✓"
                    : r.summary.verdict === "FAIL"
                      ? "✕"
                      : r.summary.verdict === "BORDERLINE"
                        ? "!"
                        : "?"}
                </span>
              ))}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function StudentDetail({ name }: { name: string }) {
  const navigate = useNavigate();
  const groups = useGroups();
  const group = groups.find((g) => g.name === name);

  if (!group) {
    return (
      <Card>
        <EmptyState
          title="Student not found"
          action={
            <Link className="btn btn-primary" to="/students" style={{ marginTop: 6 }}>
              Back to students
            </Link>
          }
        >
          No local records are linked to “{name}”.
        </EmptyState>
      </Card>
    );
  }

  const scored = group.records.filter((r) =>
    ["PASS", "BORDERLINE", "FAIL"].includes(r.summary.verdict)
  );
  const pass = scored.filter((r) => r.summary.verdict === "PASS").length;
  const avgKcal = scored.filter((r) => r.summary.kcal != null);
  const meanKcal =
    avgKcal.length > 0
      ? avgKcal.reduce((s, r) => s + (r.summary.kcal || 0), 0) / avgKcal.length
      : null;

  return (
    <>
      <div className="page-head">
        <div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => navigate("/students")}
            style={{ marginLeft: -11, marginBottom: 6 }}
          >
            <IconArrowLeft size={14} /> All students
          </button>
          <h1 className="page-title">{group.name}</h1>
          <p className="page-sub">
            Classes {group.bands.join(", ")} ·{" "}
            {group.records.length} meal
            {group.records.length === 1 ? "" : "s"} ·{" "}
            {scored.length ? `${pass}/${scored.length} PASS` : "no scored meals"}
          </p>
        </div>
        <Link className="btn btn-secondary" to="/analyze">
          New analysis
        </Link>
      </div>

      <div className="kpi-grid">
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Meals logged</span>
            <span className="kpi-ico info" aria-hidden="true">
              <IconUsers size={14} />
            </span>
          </div>
          <div className="kpi-value">{group.records.length}</div>
          <div className="kpi-foot">stored in this browser</div>
        </article>
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">PASS rate</span>
            <span className="kpi-ico pass" aria-hidden="true">
              ✓
            </span>
          </div>
          <div className="kpi-value">
            {scored.length ? formatPct(pass / scored.length, 0) : "—"}
          </div>
          <div className="kpi-foot">over scored meals</div>
        </article>
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Average energy</span>
            <span className="kpi-ico warn" aria-hidden="true">
              🔥
            </span>
          </div>
          <div className="kpi-value">{meanKcal != null ? formatNum(meanKcal, 0) : "—"}</div>
          <div className="kpi-foot">kcal per scored meal</div>
        </article>
      </div>

      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Date</th>
              <th>Dish</th>
              <th>Portion</th>
              <th>Energy</th>
              <th>Protein</th>
              <th>Coverage</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {group.records.map((r) => (
              <tr
                key={r.id}
                className="clickable"
                onClick={() => navigate(`/result/${r.id}`)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") navigate(`/result/${r.id}`);
                }}
              >
                <td>
                  <div className="cell-main">{formatDate(r.createdAt)}</div>
                  <div className="cell-sub">
                    {r.day.toUpperCase()} · band {r.band}
                  </div>
                </td>
                <td className="cell-main">{r.summary.dish || "—"}</td>
                <td className="num">
                  {r.summary.grams != null ? `${formatNum(r.summary.grams, 0)} g` : "—"}
                </td>
                <td className="num">
                  {r.summary.kcal != null ? `${formatNum(r.summary.kcal, 0)} kcal` : "—"}
                </td>
                <td className="num">
                  {r.summary.protein != null ? `${formatNum(r.summary.protein, 1)} g` : "—"}
                </td>
                <td className="num">
                  {r.summary.coverage != null ? formatPct(r.summary.coverage, 0) : "—"}
                </td>
                <td>
                  <VerdictPill verdict={r.summary.verdict} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function StudentsPage() {
  const { name } = useParams();
  return (
    <div className="page">
      {name ? (
        <StudentDetail name={decodeURIComponent(name)} />
      ) : (
        <>
          <div className="page-head">
            <div>
              <h1 className="page-title">Student records</h1>
              <p className="page-sub">
                Each photo mapped to a child — name, class band and compliance
                per date.
              </p>
            </div>
            <Link className="btn btn-primary" to="/analyze">
              Analyze meal
            </Link>
          </div>
          <p className="local-note" style={{ marginBottom: 16 }}>
            <span className="dot up" aria-hidden="true" /> Local compliance log
            — records stay in this browser until the backend adds persistence.
          </p>
          <StudentList />
        </>
      )}
    </div>
  );
}
