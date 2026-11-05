import type { AnalyzeResult } from  "../types/api";
import { CountValue } from  "../ui/section-fx";
import { formatNum, formatPct } from  "../utils/format";
import { dishLabel } from  "../services/records";
import { mealWeightView } from "./estimateView";
import { IconFlame, IconMeal, IconProtein, IconScale } from "../ui/Icon";

function Card({
  label,
  icon,
  value,
  sub,
  text = false,
  className = "",
}: {
  label: string;
  icon: React.ReactNode;
  value: React.ReactNode;
  sub?: React.ReactNode;
  text?: boolean;
  className?: string;
}) {
  return (
    <article className={`summary-card ${className}`.trim()}>
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
  const rawDishName = dishLabel(result);
  const conf = result.classification?.confidence;
  const p = result.portion;
  const mealWeight = mealWeightView(result);
  const kcal = result.nutrition?.kcal;
  const prot = result.nutrition?.protein_g;

  const items = result.items ?? [];
  const cleanLabel = (s: string) => s.replace(/\s*\(standalone(?: bowl)?\)/gi, "").trim();

  // Extract individual item names from result.items
  const detectedItemNames = items
    .map((it) => it.dish?.display_name || it.classification?.dish)
    .filter((name): name is string => Boolean(name && name.trim()))
    .map(cleanLabel);

  const dishParts = rawDishName.includes(" + ")
    ? rawDishName.split(" + ").map((s) => cleanLabel(s)).filter(Boolean)
    : [cleanLabel(rawDishName)].filter(Boolean);

  // Pool of distinct item names
  const allItemNames = detectedItemNames.length >= 2
    ? detectedItemNames
    : (dishParts.length >= 2 ? dishParts : detectedItemNames);

  const itemCount = Math.max(items.length, allItemNames.length, dishParts.length);
  const isMultiItem = result.path_used === "multi_item" || items.length >= 2 || dishParts.length >= 2;
  const isThali = isMultiItem && itemCount >= 3;

  let dishDisplayValue: string;
  let dishSub: React.ReactNode;

  if (isThali) {
    dishDisplayValue = `Indian Thali (${itemCount} Items)`;
    dishSub = (
      <span className="interval" title={allItemNames.join(" · ")}>
        {allItemNames.slice(0, 3).join(", ")}
        {allItemNames.length > 3 ? ` +${allItemNames.length - 3} more` : ""} · see Item Evidence below
      </span>
    );
  } else if (isMultiItem && allItemNames.length === 2) {
    dishDisplayValue = allItemNames.join(" + ");
    dishSub = (
      <span className="interval" title={allItemNames.join(" + ")}>
        2-item meal · individual regions segmented & weighed
      </span>
    );
  } else {
    dishDisplayValue = rawDishName || "Unrecognized dish";
    dishSub = dish ? (
      <>
        {conf != null ? `Classifier confidence ${formatPct(conf, 0)}` : "Unrecognized"}
        {result.classification?.method ? (
          <span className="interval"> · {result.classification.method}</span>
        ) : null}
      </>
    ) : undefined;
  }

  return (
    <div className="summary-grid">
      <Card
        className="meal-weight-card"
        label="Meal weight"
        icon={<IconScale size={14} />}
        value={mealWeight ? (
          <><CountValue value={mealWeight.grams} format={(v) => formatNum(v, 1)} /> g</>
        ) : "—"}
        sub={
          mealWeight ? (
            mealWeight.interval90 ? (
              <>
                90% interval {formatNum(mealWeight.interval90[0], 0)}–
                {formatNum(mealWeight.interval90[1], 0)} g
                {mealWeight.volumeMl != null && <span className="interval"> · {formatNum(mealWeight.volumeMl, 0)} ml estimated</span>}
              </>
            ) : (
            <>
              {mealWeight.volumeMl != null && `${formatNum(mealWeight.volumeMl, 0)} ml estimated`}
              {p?.base_method && <span className="interval"> · {p.base_method.replace(/_/g, " ")}</span>}
              {mealWeight.relativeSd != null && mealWeight.relativeSd > 0 && (
                <span className="interval"> · relative SD {formatPct(mealWeight.relativeSd, 0)}</span>
              )}
            </>
            )
          ) : undefined
        }
      />
      <Card
        label="Dish"
        icon={<IconMeal size={14} />}
        value={<span title={rawDishName}>{dishDisplayValue}</span>}
        text
        sub={dishSub}
      />
      <Card
        label="Energy"
        icon={<IconFlame size={14} />}
        /* Measured values settle onto the number the pipeline produced
           instead of simply appearing. */
        value={
          kcal ? (
            <>
              <CountValue value={kcal.mean} format={(v) => formatNum(v, 0)} /> kcal
            </>
          ) : (
            "—"
          )
        }
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
        icon={<IconProtein size={14} />}
        value={
          prot ? (
            <>
              <CountValue value={prot.mean} format={(v) => formatNum(v, 1)} /> g
            </>
          ) : (
            "—"
          )
        }
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
