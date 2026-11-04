import type { ReactNode } from "react";
import { useCountUp } from "./motion";

/**
 * Data-driven motion helpers. The rule this file follows: an animation only
 * ships if it communicates real information — a number settling on its
 * actual value, a measured bar growing to its measured width, a photo
 * arriving as a distinct event. Nothing here is decoration; if it stops
 * making sense, it should be deleted.
 */

/* ------------------------------ count-up ------------------------------ */

/** Animates a number from zero once, formatting every frame through `fmt`. */
export function CountValue({
  value,
  format,
}: {
  value: number;
  format: (v: number) => string;
}) {
  return <>{useCountUp(value, format)}</>;
}
