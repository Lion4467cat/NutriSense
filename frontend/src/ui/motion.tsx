import { animate, motion, useReducedMotion, type Transition, type Variants } from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";

/**
 * Wave-1 motion kit (ui-motion-polish): shared variants + transitions so
 * every page enters the same way. All consumers render inside
 * <MotionConfig reducedMotion="user"> (App.tsx), so users with
 * prefers-reduced-motion get opacity-only transitions — transforms and
 * springs are neutralized automatically by framer-motion.
 */

/** easeOutQuart-ish: fast start, long settle. */
export const EASE = [0.22, 1, 0.36, 1] as const;

export const pageVariants: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
};

export const pageTransition: Transition = { duration: 0.22, ease: EASE };

/** Wrap each routed page; keyed by pathname in App.tsx (AnimatePresence). */
export function PageFade({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
    >
      {children}
    </motion.div>
  );
}

/** Container that staggers its motion children once on mount. */
export const revealContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.04 } },
};

/** Standard child fade-up. */
export const revealItem: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: EASE } },
};

/** Springy pop (verdict icon, pills). */
export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.55 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { type: "spring", stiffness: 320, damping: 22 },
  },
};

/**
 * Wave-2 count-up: animates 0→target on mount and returns the FORMATTED
 * string via `fmt`, so pages keep their exact formatting. The final frame
 * lands exactly on `fmt(target)` — headless tests that assert the settled
 * text still see the target value semantics. prefers-reduced-motion skips
 * the animation entirely (immediate target), per MotionConfig elsewhere.
 */
export function useCountUp(
  to: number,
  fmt: (v: number) => string,
  duration = 0.9
): string {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(reduced ? to : 0);
  useEffect(() => {
    if (reduced || !Number.isFinite(to)) {
      setValue(to);
      return;
    }
    const controls = animate(0, to, {
      duration,
      ease: EASE,
      onUpdate: (v) => setValue(v),
    });
    return () => controls.stop();
  }, [to, duration, reduced]);
  return fmt(value);
}
