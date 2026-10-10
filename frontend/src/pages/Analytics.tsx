import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useRecords } from "../context/records";
import { Card, EmptyState } from "../ui/primitives";
import { IconChart } from "../ui/Icon";
import { formatNum, formatPct } from "../utils/format";
import { scored } from "../services/records";

function Donut({ parts }: { parts: { label: string; value: number; color: string }[] }) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  const R = 60;
  const C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <div className="donut-wrap">
      <div className="donut">
        <svg width="150" height="150" viewBox="0 0 150 150" role="img" aria-label="Verdict distribution">
          <circle cx="75" cy="75" r={R} fill="none" stroke="var(--surface-3)" strokeWidth="17" />
          {parts.map((p) => {
            if (p.value === 0) return null;
            const frac = p.value / total;
            const dash = `${frac * C} ${C}`;
            const el = (
              <circle
                key={p.label}
                cx="75"
                cy="75"
                r={R}
                fill="none"
                stroke={p.color}
                strokeWidth="17"
                strokeDasharray={dash}
                strokeDashoffset={-offset}
                strokeLinecap="butt"
              />
            );
            offset += frac * C;
            return el;
          })}
        </svg>
        <div className="donut-center">
          <b>{total}</b>
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

  const stats = useMemo(() => {
    const sc = scored(records);
    const pass = sc.filter((r) => r.summary.verdict === "PASS").length;
    const warn = sc.filter((r) => r.summary.verdict === "BORDERLINE").length;
    const fail = sc.filter((r) => r.summary.verdict === "FAIL").length;
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
      total: records.length,
      scored: sc.length,
      pass,
      warn,
      fail,
      complianceRate: sc.length ? pass / sc.length : null,
      avgPortion: avg(withG.map((r) => r.summary.grams)),
      avgKcal: avg(withK.map((r) => r.summary.kcal)),
      avgProtein: avg(withP.map((r) => r.summary.protein)),
      dishes,
    };
  }, [records]);

  if (records.length === 0) {
    return (
      <div className="page">
        <div className="page-head">
          <div>
            <h1 className="page-title">Analytics</h1>
            <p className="page-sub">
              Aggregated insight across your local analysis history.
            </p>
          </div>
        </div>
        <Card>
          <EmptyState
            icon={<IconChart size={20} />}
            title="No data to analyze yet"
            action={
              <Link className="btn btn-primary" to="/analyze" style={{ marginTop: 6 }}>
                Analyze your first meal
              </Link>
            }
          >
            Analytics are computed from your real analyses — nothing is
            simulated.
          </EmptyState>
        </Card>
      </div>
    );
  }

  const maxDish = Math.max(1, ...stats.dishes.map((d) => d.n));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-sub">
            Computed from {stats.total} local analysis
            {stats.total === 1 ? "" : "es"} — real records only, no sample
            data.
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
          <div className="kpi-value">{stats.total}</div>
          <div className="kpi-foot">{stats.scored} scored</div>
        </article>
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Compliance rate</span>
            <span className="kpi-ico pass" aria-hidden="true">
              ✓
            </span>
          </div>
          <div className="kpi-value">
            {stats.complianceRate != null ? formatPct(stats.complianceRate, 0) : "—"}
          </div>
          <div className="kpi-foot">PASS ÷ scored</div>
        </article>
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Average portion</span>
            <span className="kpi-ico warn" aria-hidden="true">
              ⚖
            </span>
          </div>
          <div className="kpi-value">
            {stats.avgPortion != null ? formatNum(stats.avgPortion, 0) : "—"}
          </div>
          <div className="kpi-foot">grams per scored meal</div>
        </article>
        <article className="kpi">
          <div className="kpi-top">
            <span className="kpi-label">Average energy</span>
            <span className="kpi-ico fail" aria-hidden="true">
              🔥
            </span>
          </div>
          <div className="kpi-value">
            {stats.avgKcal != null ? formatNum(stats.avgKcal, 0) : "—"}
          </div>
          <div className="kpi-foot">
            kcal · protein avg{" "}
            {stats.avgProtein != null ? `${formatNum(stats.avgProtein, 1)} g` : "—"}
          </div>
        </article>
      </div>

      <div className="dash-grid">
        <Card title="Verdict distribution" sub="Across scored analyses">
          <Donut
            parts={[
              { label: "PASS", value: stats.pass, color: "var(--pass)" },
              { label: "BORDERLINE", value: stats.warn, color: "var(--warn)" },
              { label: "FAIL", value: stats.fail, color: "var(--fail)" },
            ]}
          />
        </Card>

        <Card title="Scored share" sub="How often each verdict occurs">
          <div className="bar-rows">
            {[
              { label: "PASS", n: stats.pass, cls: "pass" },
              { label: "Borderline", n: stats.warn, cls: "warn" },
              { label: "FAIL", n: stats.fail, cls: "fail" },
            ].map((row) => (
              <div className="bar-row" key={row.label}>
                <span className="bar-label">{row.label}</span>
                <div className="bar-track">
                  <div
                    className={`bar-seg ${row.cls}`}
                    style={{
                      width: stats.scored
                        ? `${(row.n / stats.scored) * 100}%`
                        : "0%",
                    }}
                  />
                </div>
                <span className="bar-count">{row.n}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="Dish comparison"
        sub="Number of scored analyses per dish (avg energy shown on hover)"
      >
        {stats.dishes.length === 0 ? (
          <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
            No scored dishes yet.
          </p>
        ) : (
          <div className="bar-rows">
            {stats.dishes.map((d) => (
              <div
                className="bar-row"
                key={d.name}
                title={`${d.name}: ${d.n} analyses, avg ${formatNum(d.avgKcal, 0)} kcal, ${d.pass} PASS`}
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
