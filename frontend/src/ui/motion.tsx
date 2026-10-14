import { motion, type Transition, type Variants } from "framer-motion";
import type { ReactNode } from "react";

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
