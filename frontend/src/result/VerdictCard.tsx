import { motion } from "framer-motion";
import type { AnalyzeResult } from  "../types/api";
import { verdictMeta } from  "./verdicts";
import { formatPct } from  "../utils/format";
import { firstReasonText } from  "../utils/reasons";
import { EASE, popIn, revealContainer, revealItem } from "../ui/motion";

function formatDishBadge(displayName: string | null | undefined, dishId: string | undefined): { label: string; full: string } {
  const clean = (s: string) => s.replace(/\s*\(standalone(?: bowl)?\)/gi, "").trim();
  const raw = clean(displayName || dishId || "Meal");
  if (!raw.includes(" + ")) {
    return { label: raw, full: raw };
  }
  const parts = raw.split(" + ").map((s) => clean(s)).filter(Boolean);
  if (parts.length <= 2) {
    return { label: parts.join(" + "), full: raw };
  }
  return {
    label: `${parts.length} items (${parts[0]} + ${parts.length - 1} more)`,
    full: raw,
  };
}

/**
 * Wave-1 verdict reveal: staggered fade-up on first paint with a spring pop
 * on the glyph. Reduced-motion users (MotionConfig in App) get opacity-only
 * — the scales/transforms never run for them.
 */
export default function VerdictCard({ result }: { result: AnalyzeResult }) {
  const meta = verdictMeta(result.verdict);
  const VerdictIcon = meta.icon;
  const cov = result.coverage;
  const dish = result.dish;
  const conf = result.classification?.confidence;
  const dishBadge = formatDishBadge(dish?.display_name, dish?.id);

  return (
    <motion.section
      className={`verdict-card ${meta.cls}`}
      aria-labelledby="verdict-label"
      variants={revealContainer}
      initial="hidden"
      animate="show"
    >
      <motion.span className="verdict-ico" aria-hidden="true" variants={popIn}>
        <VerdictIcon size={20} />
      </motion.span>
      <motion.div style={{ minWidth: 0 }} variants={revealItem}>
        <h2 className="verdict-label" id="verdict-label">
          {meta.label}
        </h2>
        <p className="verdict-msg">{firstReasonText(result.reasons) || meta.blurb}</p>
        <motion.div
          className="verdict-meta"
          variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { duration: 0.35, ease: EASE } } }}
        >
          {dish && (
            <span className="tag" title={dishBadge.full}>
              {dishBadge.label}
              {dish.on_day === false ? " · off-menu" : ""}
            </span>
          )}
          {dish && <span className="tag">{dish.day?.toUpperCase()}</span>}
          {dish && <span className="tag">band {dish.band}</span>}
          {conf != null && <span className="tag">match {formatPct(conf, 0)}</span>}
          {result.anchor && (
            <span className="tag">
              scale: {result.anchor.tier}
              {result.anchor.depth_scale_source && result.anchor.depth_scale_source !== "none"
                ? ` · calibrated`
                : ""}
            </span>
          )}
        </motion.div>
      </motion.div>

      {cov && (
        <motion.div className="verdict-coverage" variants={revealItem}>
          <div className="cap">Coverage</div>
          <div className="big">{formatPct(cov.score, 0)}</div>
        </motion.div>
      )}
    </motion.section>
  );
}
