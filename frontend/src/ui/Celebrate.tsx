import { useMemo } from "react";
import { motion, useReducedMotion } from "framer-motion";

const COLORS = ["#22c55e", "#84cc16", "#facc15", "#38bdf8", "#f472b6", "#a78bfa"];

/**
 * Wave-3 delight: a one-shot confetti burst when a meal PASSES compliance.
 * Mounts ~18 particles at the verdict icon and unmounts after the fall —
 * nothing persists, nothing animates on reduced-motion (skipped entirely).
 */
export default function Celebrate() {
  const reduced = useReducedMotion();
  const pieces = useMemo(
    () =>
      Array.from({ length: 18 }, (_, i) => ({
        x: (Math.random() - 0.5) * 190,
        y: 90 + Math.random() * 130,
        rot: Math.random() * 540 - 270,
        delay: Math.random() * 0.12,
        color: COLORS[i % COLORS.length],
        size: 5 + Math.random() * 5,
      })),
    []
  );

  if (reduced) return null;

  return (
    <div className="celebrate" aria-hidden="true">
      {pieces.map((p, i) => (
        <motion.span
          key={i}
          className="confetti"
          style={{
            background: p.color,
            width: p.size,
            height: p.size * 0.6,
            borderRadius: 2,
          }}
          initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
          animate={{ x: p.x, y: p.y, opacity: 0, rotate: p.rot }}
          transition={{ duration: 1.15, delay: p.delay, ease: [0.16, 1, 0.3, 1] }}
        />
      ))}
    </div>
  );
}
