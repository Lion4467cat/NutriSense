import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef } from "react";
import { useExplore } from "../context/explore";
import type { Badge } from "../explore/achievements";
import { EASE } from "./motion";

/**
 * Reward toasts: a badge unlock is announced once, low and to the right,
 * with a small spark burst. They pause nothing, steal no focus and dismiss
 * themselves; the notebook keeps the permanent record.
 */
export default function AchievementToasts() {
  const { toasts, dismissToast } = useExplore();
  return (
    <div className="reward-stack" aria-live="polite">
      <AnimatePresence initial={false}>
        {toasts.map((badge) => (
          <RewardToast
            key={badge.id}
            badge={badge}
            onDone={() => dismissToast(badge.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

const SPARKS = Array.from({ length: 7 }, (_, i) => i);

function RewardToast({ badge, onDone }: { badge: Badge; onDone: () => void }) {
  const reduced = useReducedMotion();
  // The parent rebuilds the callback every render; keep the timer stable.
  const done = useRef(onDone);
  done.current = onDone;

  useEffect(() => {
    const timer = setTimeout(() => done.current(), 6500);
    return () => clearTimeout(timer);
  }, [badge.id]);

  const sparks = useMemo(
    () =>
      SPARKS.map((i) => ({
        angle: (i / SPARKS.length) * Math.PI * 2,
        distance: 16 + (i % 3) * 7,
      })),
    []
  );

  return (
    <motion.div
      className="reward-toast"
      initial={{ opacity: 0, y: 18, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.97 }}
      transition={{ duration: 0.34, ease: EASE }}
      layout
    >
      <span className="reward-mark" aria-hidden="true">
        ✦
        {!reduced &&
          sparks.map((s, i) => (
            <motion.i
              key={i}
              initial={{ x: 0, y: 0, opacity: 0.9, scale: 1 }}
              animate={{
                x: Math.cos(s.angle) * s.distance,
                y: Math.sin(s.angle) * s.distance,
                opacity: 0,
                scale: 0.4,
              }}
              transition={{ duration: 0.8, ease: EASE, delay: 0.06 }}
            />
          ))}
      </span>
      <span className="reward-body">
        <span className="reward-kicker">
          Found · {badge.secret ? "secret" : "milestone"} · +{badge.points}
        </span>
        <strong>{badge.label}</strong>
        <span className="reward-note">{badge.note}</span>
      </span>
      <button className="reward-close" onClick={onDone} aria-label="Dismiss">
        ×
      </button>
    </motion.div>
  );
}
