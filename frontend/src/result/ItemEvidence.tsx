import type { AnalyzeResult } from "../types/api";
import { motion } from "framer-motion";
import { formatNum } from "../utils/format";
import { itemWeightView } from "./estimateView";
import { resultItem, resultList } from "../ui/motion";

export default function ItemEvidence({ result }: { result: AnalyzeResult }) {
  const items = result.items ?? [];
  if (!items.length) return null;
  const semanticRegions = result.segmentation?.strategy === "wed_deeplabv3_semantic";

  return (
    <section className="card card-pad">
      <div className="card-head">
        <div>
          <h2 className="card-title">{semanticRegions ? "Detected food classes" : "Detected food items"}</h2>
          <p className="card-sub">
            {semanticRegions
              ? "Predicted class regions contribute to these estimates. WED has no serving IDs, so connected regions may merge or fragment."
              : "Food regions and their contribution to the estimate."}
          </p>
        </div>
        <span className="eyebrow">{items.length} {semanticRegions ? "classes" : "regions"}</span>
      </div>
      <motion.div className="item-evidence-list" variants={resultList} initial="hidden" animate="show">
        {items.map((item, index) => {
          const label = item.dish?.display_name || item.classification?.dish || "Unidentified item";
          const weight = itemWeightView(item);
          return (
            <motion.article className="item-evidence" key={`${label}-${index}`} variants={resultItem}>
              <div className="item-evidence-top">
                <div className="item-evidence-name">
                  <span className="item-evidence-label"><span className="item-index">{index + 1}</span><strong>{label}</strong></span>
                  <span className="item-evidence-meta-title">{semanticRegions ? "Predicted class region" : "Detected food region"}</span>
                </div>
                <div className="item-evidence-mass">
                  {weight.grams != null ? (
                    <>
                      <strong>{formatNum(weight.grams, 1)} g</strong>
                      {weight.relativeSdPercent != null && weight.relativeSdPercent > 0 && (
                        <span title="Relative standard deviation; not a 90% interval">
                          Relative SD {formatNum(weight.relativeSdPercent, 0)}%
                        </span>
                      )}
                    </>
                  ) : <span>Weight unavailable</span>}
                </div>
              </div>
              <div className="item-evidence-meta">
                {item.area_frac != null && <span>{(item.area_frac * 100).toFixed(1)}% of image</span>}
                {item.bbox && <span>Region bounds available</span>}
              </div>
              {item.reason && <p className="meal-coach-caveat">{item.reason.text}</p>}
            </motion.article>
          );
        })}
      </motion.div>
    </section>
  );
}
