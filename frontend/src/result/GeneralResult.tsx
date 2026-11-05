import type { ReactNode } from "react";
import type { AnalyzeResult } from "../types/api";
import type { DailyGoal } from "../services/goals";
import { dishLabel } from "../services/records";
import { Card } from "../ui/primitives";
import { formatNum, formatPct } from "../utils/format";
import { explainReason, toReasons } from "../utils/reasons";
import { reasonTone } from "./verdicts";
import SummaryCards from "./SummaryCards";
import MealRegionFigure from "./MealRegionFigure";

/**
 * General-mode result (spec 002, ADR 0003): grams + nutrients + each
 * nutrient's share of the Daily goal. There is NO verdict badge here — the
 * Verdict vocabulary stays a School-mode compliance concept. The no-card
 * estimate disclaimer still leads when the backend led its reasons with
 * no_reference_card, and a recognized off-menu dish renders its estimates
 * with an honest "no compliance verdict" note instead of an error state.
 */

function ShareRow({
  name,
  unit,
  value,
  interval,
  goal,
  digits,
}: {
  name: string;
  unit: string;
  value: number | null;
  interval?: readonly [number, number] | undefined;
  goal: number | null;
  digits: number;
}) {
  const share =
    value != null && goal != null && goal > 0 && Number.isFinite(value)
      ? value / goal
      : null;
  const width = share == null ? 0 : Math.min(100, share * 100);
  return (
    <div className="goal-row">
      <div className="goal-row-head">
        <span className="nutrient-name">{name}</span>
        <span className="goal-share">
          {value == null ? (
            "—"
          ) : share == null ? (
            `${formatNum(value, digits)} ${unit}`
          ) : (
            <>
              {formatNum(value, digits)} {unit}
              <span className="goal-share-pct"> · {Math.round(share * 100)}% of your day</span>
            </>
          )}
        </span>
      </div>
      <div
        className="goal-track"
        role="img"
        aria-label={
          value == null
            ? `${name}: no estimate`
            : share == null
              ? `${name}: ${formatNum(value, digits)} ${unit}, no daily goal set`
              : `${name}: ${formatNum(value, digits)} ${unit}, ${Math.round(
                  share * 100
                )} percent of the ${formatNum(goal, digits)} ${unit} daily goal`
        }
      >
        <div className="goal-fill" style={{ width: `${width}%` }} />
      </div>
      <div className="nutrient-foot">
        <span>
          {interval
            ? `90% interval ${formatNum(interval[0], digits)}–${formatNum(interval[1], digits)} ${unit}`
            : "no interval available"}
        </span>
        <span className="sep">
          {goal == null
            ? "set your profile in Settings to see goal shares"
            : `daily goal ${formatNum(goal, digits)} ${unit}`}
        </span>
      </div>
    </div>
  );
}

export default function GeneralResult({
  result,
  goal,
  summaryAddon,
  photo,
  demo = false,
}: {
  result: AnalyzeResult;
  goal: DailyGoal;
  summaryAddon?: ReactNode;
  photo?: string | null;
  demo?: boolean;
}) {
  const reasons = toReasons(result.reasons);
  const offMenuReason = reasons.find((reason) => reason.kind === "off_menu_dish");
  const noCardReason = reasons.find((reason) => reason.kind === "no_reference_card");
  const offMenu = !!offMenuReason;
  const noCard = !!noCardReason;
  const detailReasons = reasons.filter((reason) =>
    ["zoom", "unrecognized", "unreadable", "weight_head_unavailable", "stage_failed"].includes(reason.kind)
  );
  const hasEstimates = !!result.portion && !!result.nutrition;
  const kcal = result.nutrition?.kcal;
  const prot = result.nutrition?.protein_g;

  return (
    <>
      {offMenu && (
        <div className="banner info" style={{ marginBottom: 16 }}>
          <span aria-hidden="true">i</span>
          <div>
            <strong>Not a school-menu dish — no compliance verdict</strong>
            {offMenuReason ? explainReason(offMenuReason) : "This meal is outside the school menu."}
          </div>
        </div>
      )}
      {noCard && (
        <div className="banner warn" style={{ marginBottom: 16 }}>
          <span aria-hidden="true">!</span>
          <div>
            <strong>Estimated weight — no reference card</strong>
            {noCardReason ? explainReason(noCardReason) : "No reference card was detected, so portion weight is estimated from the photo."}
          </div>
        </div>
      )}

      {hasEstimates ? (
        <>
          <div className={`general-overview${photo ? " has-photo" : ""}`}>
            {photo && (
              <MealRegionFigure photo={photo} items={result.items ?? []} demo={demo} />
            )}
            <SummaryCards result={result} />
          </div>
          {summaryAddon}

          <Card
            title="Share of your Daily goal"
            sub={
              goal.source === "custom"
                ? "Your own goal — editable in Settings"
                : goal.source === "who"
                  ? goal.defaulted
                    ? "WHO default for the first-served profile — set your profile in Settings"
                    : "WHO default for your profile — you can override it in Settings"
                  : "No goal available — set your profile in Settings"
            }
          >
            <ShareRow
              name="Energy"
              unit="kcal"
              value={kcal?.mean ?? null}
              interval={kcal?.interval_90}
              goal={goal.kcal}
              digits={0}
            />
            <ShareRow
              name="Protein"
              unit="g"
              value={prot?.mean ?? null}
              interval={prot?.interval_90}
              goal={goal.proteinG}
              digits={1}
            />
          </Card>
        </>
      ) : (
        <>
          {photo && (
            <MealRegionFigure photo={photo} items={result.items ?? []} demo={demo} className="result-photo-general" />
          )}
          <Card title="No nutrition estimate">
            <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
              {result.dish
                ? "This capture produced no grams or nutrients."
                : "We could not recognize a dish in this photo — try again with the whole vessel in frame."}
            </p>
          </Card>
          {summaryAddon}
        </>
      )}

      <Card title="About this estimate" sub="What influenced the result.">
        {detailReasons.length === 0 ? (
          <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>
            No additional measurement notes were returned for this estimate.
          </p>
        ) : (
          <ul className="list-clean reason-list">
            {detailReasons.map((r, i) => {
              const ico = reasonTone(r, result.verdict);
              return (
                <li className="reason-item" key={i}>
                  <span className={`r-ico ${ico}`} aria-hidden="true">
                    {ico === "good" ? "✓" : ico === "bad" ? "✕" : "i"}
                  </span>
                  <span>{explainReason(r)}</span>
                </li>
              );
            })}
          </ul>
        )}
        {result.dish && (
          <p className="muted" style={{ fontSize: "var(--fs-sm)", marginTop: 10 }}>
            Recognized as{" "}
            <strong>{dishLabel(result) || result.dish.id}</strong>
            {result.items && result.items.length >= 2 ? (
              ` · ${result.items.length} segmented food items`
            ) : (
              result.classification?.confidence != null &&
              ` · classifier confidence ${formatPct(result.classification.confidence, 0)}`
            )}
            .
          </p>
        )}
      </Card>
    </>
  );
}
