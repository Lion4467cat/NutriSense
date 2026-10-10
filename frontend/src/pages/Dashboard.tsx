import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMenu } from "../context/menu";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { Card, EmptyState, VerdictPill } from "../ui/primitives";
import {
  IconCamera,
  IconChart,
  IconHistory,
} from "../ui/Icon";
import type { Verdict } from "../types/api";
import { formatDate, formatNum, formatPct, localDateKey } from "../utils/format";
import type { AnalysisRecord } from "../services/records";

const SCORED: Verdict[] = ["PASS", "BORDERLINE", "FAIL"];

function scored(records: AnalysisRecord[]) {
  return records.filter((r) => SCORED.includes(r.summary.verdict));
}

function daysAgo(n: number): number {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.getTime();
}

function Kpi({
  label,
  value,
  foot,
  trend,
  icon,
  cls,
}: {
  label: string;
  value: string;
  foot: string;
  trend?: { dir: "up" | "down" | "flat"; text: string };
  icon: React.ReactNode;
  cls: "pass" | "warn" | "fail" | "info";
}) {
  return (
    <article className="kpi">
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        <span className={`kpi-ico ${cls}`} aria-hidden="true">
          {icon}
        </span>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-foot">
        <span>{foot}</span>
        {trend && <span className={`kpi-trend ${trend.dir}`}>{trend.text}</span>}
      </div>
    </article>
  );
}

function ComplianceOverview({ records }: { records: AnalysisRecord[] }) {
  const byDay = new Map<string, Record<string, number>>();
  for (const r of records.slice(0, 60)) {
    const key = localDateKey(r.createdAt);
    const bucket = byDay.get(key) || { PASS: 0, BORDERLINE: 0, FAIL: 0, other: 0 };
    if (SCORED.includes(r.summary.verdict)) bucket[r.summary.verdict] += 1;
    else bucket.other += 1;
    byDay.set(key, bucket);
  }
  const days = [...byDay.entries()].sort((a, b) => a[0].localeCompare(b[0])).slice(-14);
  const max = Math.max(1, ...days.map(([, v]) => v.PASS + v.BORDERLINE + v.FAIL + v.other));

  if (days.length === 0) return null;

  return (
    <div className="compliance-chart">
      <div className="chart-legend">
        <span><span className="legend-dot" style={{ background: "var(--pass)" }} />Pass</span>
        <span><span className="legend-dot" style={{ background: "var(--warn)" }} />Borderline</span>
        <span><span className="legend-dot" style={{ background: "var(--fail)" }} />Fail</span>
        <span><span className="legend-dot" style={{ background: "var(--text-3)" }} />Unscored</span>
      </div>
      <div className="day-chart" role="img" aria-label="Compliance verdicts per day">
        {days.map(([day, v]) => {
          const total = v.PASS + v.BORDERLINE + v.FAIL + v.other;
          const h = (total / max) * 100;
          return (
            <div className="day-col" key={day} title={`${day}: ${total} analyses`}>
              <div className="day-stack" style={{ height: `${h}%` }}>
                {v.PASS > 0 && (
                  <div className="seg-pass" style={{ flex: v.PASS }} />
                )}
                {v.BORDERLINE > 0 && (
                  <div className="seg-warn" style={{ flex: v.BORDERLINE }} />
                )}
                {v.FAIL > 0 && <div className="seg-fail" style={{ flex: v.FAIL }} />}
                {v.other > 0 && (
                  <div className="seg-neutral" style={{ flex: v.other }} />
                )}
              </div>
              <div className="day-label">{day.slice(5)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { records } = useRecords();
  const { menuError, apiUp } = useMenu();
  const { prefs, setPrefs } = usePrefs();
  const navigate = useNavigate();

  const sc = scored(records);
  const pass = sc.filter((r) => r.summary.verdict === "PASS").length;
  const warn = sc.filter((r) => r.summary.verdict === "BORDERLINE").length;
  const fail = sc.filter((r) => r.summary.verdict === "FAIL").length;

  const now = Date.now();
  const recent = records.filter((r) => Date.parse(r.createdAt) >= daysAgo(7)).length;
  const prev = records.filter(
    (r) => Date.parse(r.createdAt) >= daysAgo(14) && Date.parse(r.createdAt) < daysAgo(7)
  ).length;
  const delta = recent - prev;
  const trend =
    records.length === 0
      ? undefined
      : {
          dir: delta > 0 ? ("up" as const) : delta < 0 ? ("down" as const) : ("flat" as const),
          text: delta > 0 ? `+${delta} this week` : delta < 0 ? `${delta} this week` : "steady",
        };

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const storedName = prefs.userName.trim();
  const first = storedName ? storedName.split(/\s+/)[0] : "";
  const [nameDraft, setNameDraft] = useState(storedName);
  const [editingName, setEditingName] = useState(false);
  const saveName = () => {
    setPrefs({ userName: nameDraft.trim() });
    setEditingName(false);
  };

  const rate = (n: number) => (sc.length ? formatPct(n / sc.length, 0) : "—");

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">
            {greeting}
            {first ? `, ${first}` : ", NutriSense"}
            {editingName ? (
              <input
                className="input name-input"
                type="text"
                autoFocus
                maxLength={40}
                placeholder="Your name"
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                onBlur={saveName}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveName();
                }}
              />
            ) : (
              <button
                className={storedName ? "name-tag named" : "name-tag"}
                title="Edit display name"
                aria-label={storedName ? "Edit display name" : "Add your display name"}
                onClick={() => {
                  setNameDraft(storedName);
                  setEditingName(true);
                }}
              >
                {storedName || "+ Add your name"}
              </button>
            )}
          </h1>
          <p className="page-sub">
            Monitor meal quality, nutrition coverage, and PM POSHAN compliance.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/analyze")}>
          <IconCamera size={16} /> Analyze New Meal
        </button>
      </div>

      {apiUp === false && (
        <div className="banner error" style={{ marginBottom: 16 }}>
          <span aria-hidden="true">✕</span>
          <div>
            <strong>Backend unreachable</strong>
            Local history is still available — new analyses need the API.
          </div>
        </div>
      )}
      {menuError && apiUp !== false && (
        <div className="banner warn" style={{ marginBottom: 16 }}>
          <span aria-hidden="true">!</span>
          <div>Menu could not be loaded — some fields may be unavailable.</div>
        </div>
      )}

      {records.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconCamera size={20} />}
            title="No analyses yet"
            action={
              <Link className="btn btn-primary" to="/analyze" style={{ marginTop: 6 }}>
                Analyze your first meal
              </Link>
            }
          >
            Your meal analyses will appear here with verdicts, coverage and
            uncertainty for every capture.
          </EmptyState>
        </Card>
      ) : (
        <>
          <div className="kpi-grid">
            <Kpi
              label="Meals analyzed"
              value={String(records.length)}
              foot="stored in this browser"
              trend={trend}
              icon={<IconHistory size={14} />}
              cls="info"
            />
            <Kpi
              label="PASS rate"
              value={rate(pass)}
              foot={`${pass} of ${sc.length} scored`}
              icon="✓"
              cls="pass"
            />
            <Kpi
              label="BORDERLINE rate"
              value={rate(warn)}
              foot={`${warn} of ${sc.length} scored`}
              icon="!"
              cls="warn"
            />
            <Kpi
              label="FAIL rate"
              value={rate(fail)}
              foot={`${fail} of ${sc.length} scored`}
              icon="✕"
              cls="fail"
            />
          </div>

          <div className="dash-grid">
            <Card
              title="Compliance overview"
              sub="Verdicts per capture day — from your local analysis history"
              action={
                <Link className="btn btn-ghost btn-sm" to="/analytics">
                  <IconChart size={14} /> Analytics
                </Link>
              }
            >
              <ComplianceOverview records={records} />
            </Card>

            <Card title="Recent analyses" sub="Newest first">
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {records.slice(0, 6).map((r) => (
                  <button
                    key={r.id}
                    className="student-card"
                    style={{ padding: "10px 12px", boxShadow: "none" }}
                    onClick={() => navigate(`/result/${r.id}`)}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        justifyContent: "space-between",
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div className="cell-main" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                          {r.summary.dish || "Unrecognized dish"}
                        </div>
                        <div className="cell-sub">
                          {formatDate(r.createdAt)}
                          {r.student ? ` · ${r.student.name}` : ""}
                        </div>
                      </div>
                      <VerdictPill verdict={r.summary.verdict} />
                    </div>
                  </button>
                ))}
              </div>
            </Card>
          </div>

          <Card
            title="Recent analyses"
            sub="Full list with nutrition and coverage"
            pad={false}
            action={
              <Link className="btn btn-ghost btn-sm" to="/history">
                View all
              </Link>
            }
          >
            <div className="table-wrap" style={{ border: 0 }}>
              <table className="data">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Dish</th>
                    <th>Portion</th>
                    <th>Energy</th>
                    <th>Coverage</th>
                    <th>Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {records.slice(0, 6).map((r) => (
                    <tr
                      key={r.id}
                      className="clickable"
                      onClick={() => navigate(`/result/${r.id}`)}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") navigate(`/result/${r.id}`);
                      }}
                    >
                      <td>{formatDate(r.createdAt)}</td>
                      <td>
                        <div className="cell-main">{r.summary.dish || "—"}</div>
                        <div className="cell-sub">
                          {r.student ? r.student.name : r.day.toUpperCase()}
                        </div>
                      </td>
                      <td className="num">{r.summary.grams != null ? `${formatNum(r.summary.grams, 0)} g` : "—"}</td>
                      <td className="num">{r.summary.kcal != null ? `${formatNum(r.summary.kcal, 0)} kcal` : "—"}</td>
                      <td className="num">{r.summary.coverage != null ? formatPct(r.summary.coverage, 0) : "—"}</td>
                      <td>
                        <VerdictPill verdict={r.summary.verdict} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
