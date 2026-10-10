import type { AnalyzeResult } from  "../types/api";
import { formatNum, formatPct } from  "../utils/format";
import { dishLabel } from  "../services/records";

function Card({
  label,
  icon,
  value,
  sub,
  text = false,
}: {
  label: string;
  icon: string;
  value: string;
  sub?: React.ReactNode;
  text?: boolean;
}) {
  return (
    <article className="summary-card">
      <div className="sc-label">
        <span aria-hidden="true">{icon}</span>
        {label}
      </div>
      <div className={`sc-value${text ? " text" : ""}`}>{value}</div>
      {sub && <div className="sc-sub">{sub}</div>}
    </article>
  );
}

export default function SummaryCards({ result }: { result: AnalyzeResult }) {
  const dish = result.dish || result.classification;
  const dishName = dishLabel(result);
  const conf = result.classification?.confidence;
  const p = result.portion;
  const kcal = result.nutrition?.kcal;
  const prot = result.nutrition?.protein_g;

  return (
    <div className="summary-grid">
      <Card
        label="Dish"
        icon="🍽"
        value={dishName}
        text
        sub={
          dish ? (
            <>
              {conf != null ? `Confidence ${formatPct(conf, 0)}` : "Unrecognized"}
              {result.classification?.method ? (
                <span className="interval"> · {result.classification.method}</span>
              ) : null}
            </>
          ) : undefined
        }
      />
      <Card
        label="Portion"
        icon="⚖"
        value={p ? `${formatNum(p.grams, 1)} g` : "—"}
        sub={
          p ? (
            <>
              {formatNum(p.volume_ml, 0)} ml estimated
              <span className="interval">
                {" "}
                · {p.base_method.replace(/_/g, " ")}
              </span>
            </>
          ) : undefined
        }
      />
      <Card
        label="Energy"
        icon="🔥"
        value={kcal ? `${formatNum(kcal.mean, 0)} kcal` : "—"}
        sub={
          kcal ? (
            <span className="interval">
              90% interval {formatNum(kcal.interval_90[0], 0)}–
              {formatNum(kcal.interval_90[1], 0)} kcal
            </span>
          ) : undefined
        }
      />
      <Card
        label="Protein"
        icon="🧬"
        value={prot ? `${formatNum(prot.mean, 1)} g` : "—"}
        sub={
          prot ? (
            <span className="interval">
              90% interval {formatNum(prot.interval_90[0], 1)}–
              {formatNum(prot.interval_90[1], 1)} g
            </span>
          ) : undefined
        }
      />
    </div>
  );
}
