import { useMemo } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { useRecords } from "../context/records";
import { usePrefs } from "../context/prefs";
import { Card, EmptyState } from "../ui/primitives";
import { CountValue } from "../ui/section-fx";
import { EASE } from "../ui/motion";
import { IconChart, IconCheck, IconFlame, IconScale } from "../ui/Icon";
import { formatNum, formatPct } from "../utils/format";
import { scored, tally } from "../services/records";

function Donut({ parts }: { parts: { label: string; value: number; color: string }[] }) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  const R = 60;
  const C = 2 * Math.PI * R;
  const reduced = useReducedMotion();
  let offset = 0;
  return (
    <div className="donut-wrap">
      <div className="donut">
        <svg width="150" height="150" viewBox="0 0 150 150" role="img" aria-label="Verdict distribution">
          <circle cx="75" cy="75" r={R} fill="none" stroke="var(--surface-3)" strokeWidth="17" />
          {parts.map((p, i) => {
            if (p.value === 0) return null;
            const frac = p.value / total;
            // Each slice grows from its own start angle to its real share
            // of the ring, slice by slice, so the distribution is read as
            // it is built. Dashoffset stays put: nothing slides around.
            const dash = `${frac * C} ${C}`;
            const el = (
              <motion.circle
                key={p.label}
                cx="75"
                cy="75"
                r={R}
                fill="none"
                stroke={p.color}
                strokeWidth="17"
                strokeDashoffset={-offset}
                strokeLinecap="butt"
                initial={reduced ? false : { strokeDasharray: `0.001 ${C}` }}
                animate={{ strokeDasharray: dash }}
                transition={
                  reduced
                    ? { duration: 0 }
                    : { duration: 0.85, ease: EASE, delay: 0.12 + i * 0.12 }
                }
              />
            );
            offset += frac * C;
            return el;
          })}
        </svg>
        <div className="donut-center">
          <b>
            <CountValue value={total} format={(v) => String(Math.round(v))} />
          </b>
          <span>scored</span>
        </div>
      </div>
      <div className="donut-legend">
        {parts.map((p) => (
          <div className="row" key={p.label}>
            <span className="legend-dot" style={{ background: p.color }} />
            {p.label}
            <b>{p.value}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const { records } = useRecords();
  const { prefs } = usePrefs();
  const general = (prefs.mode ?? "school") === "general";
  const modeRecords = useMemo(
    () => records.filter((r) => (r.mode ?? "school") === (general ? "general" : "school")),
    [records, general]
  );

  const stats = useMemo(() => {
    const sc = general ? modeRecords : scored(modeRecords);
    const t = general ? { pass: 0, warn: 0, fail: 0, scored: 0 } : tally(modeRecords);
    const { pass, warn, fail } = t;
    const withG = sc.filter((r) => r.summary.grams != null);
    const withK = sc.filter((r) => r.summary.kcal != null);
    const withP = sc.filter((r) => r.summary.protein != null);
    const avg = (vals: (number | null | undefined)[]) =>
      vals.length
        ? vals.reduce<number>((s, v) => s + (v || 0), 0) / vals.length
        : null;

    const byDish = new Map<string, { n: number; kcal: number; pass: number }>();
    for (const r of sc) {
      const key = r.summary.dish || "Unrecognized";
      const e = byDish.get(key) || { n: 0, kcal: 0, pass: 0 };
      e.n += 1;
      e.kcal += r.summary.kcal || 0;
      if (r.summary.verdict === "PASS") e.pass += 1;
      byDish.set(key, e);
    }
    const dishes = [...byDish.entries()]
      .map(([name, v]) => ({ name, ...v, avgKcal: v.n ? v.kcal / v.n : 0 }))
      .sort((a, b) => b.n - a.n);

    return {
      total: modeRecords.length,
      scored: t.scored,
      pass,
      warn,
      fail,
      complianceRate: t.scored ? t.pass / t.scored : null,
      avgPortion: avg(withG.map((r) => r.summary.grams)),
      avgKcal: avg(withK.map((r) => r.summary.kcal)),
      avgProtein: avg(withP.map((r) => r.summary.protein)),
      dishes,
    };
  }, [general, modeRecords]);

  if (stats.total === 0) {
    return (
      <div className="page page-insights">
        <div className="page-head">
          <div>
            <h1 className="page-title">Analytics</h1>
            <p className="page-sub">
              {general
                ? "Nutrition summaries from your General-mode meal journal."
                : "Compliance summaries from your School-mode analysis history."}
            </p>
          </div>
        </div>
        <Card>
          <EmptyState
            icon={<IconChart size={20} />}
            title={`No ${general ? "General" : "School"}-mode meals yet`}
            action={
              <Link className="btn btn-primary" to="/analyze" style={{ marginTop: 6 }}>
                Analyze your first meal
              </Link>
            }
          >
            Analytics use saved analyses from this mode only. No sample data is
            shown.
          </EmptyState>
        </Card>
      </div>
    );
  }

  const maxDish = Math.max(1, ...stats.dishes.map((d) => d.n));

  return (
    <div className="page page-insights">
      <div className="page-head">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-sub">
            Computed from {stats.total} {general ? "General-mode meal" : "School-mode analysis"}
            {stats.total === 1 ? "" : "s"} — real records only, no sample data.
          </p>
        </div>
      </div>

      <div className="kpi-grid">
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Total meals analyzed</span>
            <span className="kpi-ico info" aria-hidden="true">
              <IconChart size={14} />
            </span>
          </div>
          <div className="kpi-value">
            <CountValue value={stats.total} format={(v) => String(Math.round(v))} />
          </div>
          <div className="kpi-foot">{general ? "meal estimates" : `${stats.scored} scored`}</div>
        </article>
        {!general && <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Compliance rate</span>
            <span className="kpi-ico pass" aria-hidden="true">
              <IconCheck size={14} />
            </span>
          </div>
          <div className="kpi-value">
            {stats.complianceRate != null ? (
              <CountValue
                value={stats.complianceRate}
                format={(v) => formatPct(v, 0)}
              />
            ) : (
              "—"
            )}
          </div>
          <div className="kpi-foot">Pass divided by scored meals</div>
        </article>}
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Average portion</span>
            <span className="kpi-ico warn" aria-hidden="true">
              <IconScale size={14} />
            </span>
          </div>
          <div className="kpi-value">
            {stats.avgPortion != null ? (
              <CountValue value={stats.avgPortion} format={(v) => formatNum(v, 0)} />
            ) : (
              "—"
            )}
          </div>
          <div className="kpi-foot">grams per meal with an estimate</div>
        </article>
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Average energy</span>
            <span className="kpi-ico fail" aria-hidden="true">
              <IconFlame size={14} />
            </span>
          </div>
          <div className="kpi-value">
            {stats.avgKcal != null ? (
              <CountValue value={stats.avgKcal} format={(v) => formatNum(v, 0)} />
            ) : (
              "—"
            )}
          </div>
          <div className="kpi-foot">
            kcal · protein avg{" "}
            {stats.avgProtein != null ? `${formatNum(stats.avgProtein, 1)} g` : "—"}
          </div>
        </article>
      </div>

      {!general && <div className="dash-grid">
        <Card title="Verdict distribution" sub="Across scored analyses">
          <Donut
            parts={[
              { label: "Pass", value: stats.pass, color: "var(--pass)" },
              { label: "Borderline", value: stats.warn, color: "var(--warn)" },
              { label: "Fail", value: stats.fail, color: "var(--fail)" },
            ]}
          />
        </Card>

      </div>}

      <Card
        title={general ? "Meals by dish" : "Dish comparison"}
        sub={general
          ? "Number of General-mode meals per dish (average energy shown on hover)"
          : "Number of scored analyses per dish (average energy shown on hover)"}
      >
        {stats.dishes.length === 0 ? (
          <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
            No dishes with meal estimates yet.
          </p>
        ) : (
          <div className="bar-rows">
            {stats.dishes.map((d) => (
              <div
                className="bar-row"
                key={d.name}
                title={general
                  ? `${d.name}: ${d.n} meals, average ${formatNum(d.avgKcal, 0)} kcal`
                  : `${d.name}: ${d.n} analyses, average ${formatNum(d.avgKcal, 0)} kcal, ${d.pass} pass`}
              >
                <span className="bar-label">{d.name}</span>
                <div className="bar-track">
                  <div
                    className="bar-seg pass"
                    style={{ width: `${(d.n / maxDish) * 100}%`, opacity: 0.85 }}
                  />
                </div>
                <span className="bar-count">{d.n}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
