import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from "framer-motion";
import { useState, type PointerEvent, type ReactNode } from "react";
import { EASE } from "./motion";

/**
 * Exploration kit (desertant-inspired): the gestures a visitor can notice
 * and play with — a panel that leans toward the cursor, a button that
 * answers to a magnet, a ring that fills as sections are found.
 *
 * Every effect is opt-out. `prefers-reduced-motion` removes the transforms
 * entirely rather than shortening them, and pointer effects only run for a
 * mouse (`pointerType === "mouse"`), so touch users never see a card stuck
 * mid-tilt. Scroll reveals stay in `motion.tsx` (revealContainer /
 * scrollReveal) — one vocabulary, not two.
 */

/* -------------------------------- tilt --------------------------------- */

/**
 * Pointer-tracked tilt with a soft accent sheen under the cursor. The
 * translate is a few degrees at most — enough to feel alive, not enough to
 * make text swim.
 */
export function TiltPanel({
  children,
  className = "",
  max = 4,
}: {
  children: ReactNode;
  className?: string;
  max?: number;
}) {
  const reduced = useReducedMotion();
  const rotX = useMotionValue(0);
  const rotY = useMotionValue(0);
  const glowX = useMotionValue(50);
  const glowY = useMotionValue(50);
  const springX = useSpring(rotX, { stiffness: 220, damping: 24 });
  const springY = useSpring(rotY, { stiffness: 220, damping: 24 });
  const sheen = useMotionTemplate`radial-gradient(220px circle at ${glowX}% ${glowY}%, var(--accent-soft), transparent 62%)`;
  const [active, setActive] = useState(false);

  if (reduced) {
    return <div className={`tilt ${className}`}>{children}</div>;
  }

  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (e.pointerType !== "mouse") return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    rotX.set((0.5 - py) * max * 2);
    rotY.set((px - 0.5) * max * 2);
    glowX.set(px * 100);
    glowY.set(py * 100);
    setActive(true);
  };

  const onLeave = () => {
    rotX.set(0);
    rotY.set(0);
    setActive(false);
  };

  return (
    <motion.div
      className={`tilt ${className}`}
      style={{ rotateX: springX, rotateY: springY, transformPerspective: 1100 }}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
    >
      {children}
      <motion.span
        className="tilt-sheen"
        aria-hidden="true"
        style={{ background: sheen, opacity: active ? 0.5 : 0 }}
        transition={{ duration: 0.2 }}
      />
    </motion.div>
  );
}

/* ------------------------------- magnetic ------------------------------ */

/** A child that leans a few pixels toward the cursor, then springs home. */
export function Magnetic({
  children,
  className,
  strength = 8,
}: {
  children: ReactNode;
  className?: string;
  strength?: number;
}) {
  const reduced = useReducedMotion();
  const x = useSpring(useMotionValue(0), { stiffness: 320, damping: 18 });
  const y = useSpring(useMotionValue(0), { stiffness: 320, damping: 18 });

  if (reduced) return <div className={`magnet ${className ?? ""}`}>{children}</div>;

  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (e.pointerType !== "mouse") return;
    const rect = e.currentTarget.getBoundingClientRect();
    x.set(((e.clientX - rect.left) / rect.width - 0.5) * strength * 2);
    y.set(((e.clientY - rect.top) / rect.height - 0.5) * strength * 2);
  };
  const onLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      className={`magnet ${className ?? ""}`}
      style={{ x, y }}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
    >
      {children}
    </motion.div>
  );
}

/* ----------------------------- progress ring --------------------------- */

/** Small SVG ring that fills to `value` (0–1) with a springy stroke. */
export function ProgressRing({
  value,
  size = 30,
  stroke = 2.5,
  label,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
}) {
  const reduced = useReducedMotion();
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const target = Math.max(0, Math.min(1, value));
  return (
    <span
      className="ring"
      style={{ width: size, height: size }}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--surface-3)"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={false}
          animate={{ strokeDashoffset: c * (1 - target) }}
          transition={{ duration: reduced ? 0 : 0.7, ease: EASE }}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
    </span>
  );
}
