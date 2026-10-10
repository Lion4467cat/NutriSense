import type { AnalyzeResult, NutrientRow, Policy } from  "../types/api";
import { FALLBACK_POLICY } from  "../types/api";
import { Card } from  "../ui/primitives";
import { formatNum, formatPct } from  "../utils/format";

const LABELS: Record<string, string> = {
  kcal: "Energy",
  protein_g: "Protein",
};
const UNITS: Record<string, string> = { kcal: "kcal", protein_g: "g" };

function IntervalBar({
  name,
  unit,
  row,
  p,
  policy,
}: {
  name: string;
  unit: string;
  row: NutrientRow;
  p: number | undefined;
  policy: Policy;
}) {
  const [lo, hi] = row.interval_90;
  const domain = Math.max(hi, row.min) * 1.18 || 1;
  const pct = (v: number) => `${Math.min(100, Math.max(0, (v / domain) * 100))}%`;
  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1));
  const pCls =
    p == null
      ? "warn"
      : p >= policy.pass_p
        ? "good"
        : p <= policy.fail_p
          ? "bad"
          : "warn";

  return (
    <div className="nutrient">
      <div className="nutrient-head">
        <span className="nutrient-name">{name}</span>
        <span className={`p-chip ${pCls}`}>
          {p == null ? "P unavailable" : `P = ${p.toFixed(2)}`}
          {p != null && (
            <span className="visually-hidden">
              {" "}
              probability of meeting the minimum
            </span>
          )}
        </span>
      </div>

      <div
        className="nutrient-track"
        role="img"
        aria-label={`${name}: mean ${fmt(row.mean)} ${unit}, 90 percent interval ${fmt(
          lo
        )} to ${fmt(hi)} ${unit}, minimum ${fmt(row.min)} ${unit}`}
      >
        <div className="nt-rail" />
        <div
          className="nt-interval"
          style={{ left: pct(lo), width: `calc(${pct(hi)} - ${pct(lo)})` }}
          title={`90% interval ${fmt(lo)}–${fmt(hi)} ${unit}`}
        />
        <div
          className="nt-mean"
          style={{ left: pct(row.mean) }}
          title={`mean ${fmt(row.mean)} ${unit}`}
        />
        <div
          className="nt-min"
          style={{ left: pct(row.min) }}
          data-label={`min ${fmt(row.min)}`}
        />
      </div>

      <div className="nutrient-foot">
        <span>
          mean {fmt(row.mean)} {unit}
        </span>
        <span className="sep">
          90% interval {fmt(lo)}–{fmt(hi)} {unit}
        </span>
        <span className="sep">
          {row.headroom_at_interval_low >= 0 ? "+" : ""}
          {fmt(row.headroom_at_interval_low)} {unit} at interval low vs min
        </span>
        <span className="sep">
          P(min) {p == null ? "—" : formatPct(p, 0)}
        </span>
      </div>
    </div>
  );
}

export default function NutrientIntervals({ result }: { result: AnalyzeResult }) {
  const comp = result.compliance;
  const policy = result.policy ?? FALLBACK_POLICY;
  if (!comp || !comp.nutrients || Object.keys(comp.nutrients).length === 0) {
    return (
      <Card title="Uncertainty intervals">
        <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
          Nutrient probabilities are unavailable for this verdict. The backend
          reports uncertainty for every scored analysis — this capture exited
          before Monte Carlo sampling.
        </p>
      </Card>
    );
  }

  return (
    <Card
      title="Nutrition vs PM POSHAN minimum"
      sub="Monte Carlo 90% interval against the class-band minimum — never a single misleading bar."
    >
      {Object.entries(comp.nutrients).map(([key, row]) => (
        <IntervalBar
          key={key}
          name={LABELS[key] || key}
          unit={UNITS[key] || ""}
          row={row}
          p={comp.probs?.[key]}
          policy={policy}
        />
      ))}
      <p className="card-sub" style={{ marginTop: 12 }}>
        Interval from {result.nutrition?.n ?? 4000} fixed-seed samples · P = P(at
        or above minimum) computed by the backend.
      </p>
    </Card>
  );
}
