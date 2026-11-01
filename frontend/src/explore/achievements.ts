import type { Storage } from "../services/storage";

/**
 * Exploration layer (desertant-inspired playfulness, honest by design):
 * browsing the app is the reward loop — no scores, no streaks to keep,
 * nothing that punishes a user for not coming back. Every rule here is a
 * pure function of state + time so the shell can persist it through the
 * injected Storage seam and tests can settle it deterministically.
 */

export const EXPLORE_KEY = "nutrisense.explore.v1";

/** Sections a curious user can wander into (result views belong to history). */
export type AreaId =
  | "home"
  | "analyze"
  | "history"
  | "insights"
  | "students"
  | "menu"
  | "settings";

export interface Area {
  id: AreaId;
  label: string;
  /** Nav order — also the direction of the page transition. */
  to: string;
  hint: string;
}

export const AREAS: readonly Area[] = [
  { id: "home", label: "Home", to: "/", hint: "The overview and the how-it-works story." },
  { id: "analyze", label: "Analyze", to: "/analyze", hint: "The meal studio — where a photo becomes grams." },
  { id: "history", label: "History", to: "/history", hint: "Every saved analysis, newest first." },
  { id: "insights", label: "Insights", to: "/analytics", hint: "Trends across the meals you saved." },
  { id: "students", label: "Student records", to: "/students", hint: "Per-student meal logs." },
  { id: "menu", label: "Menu & standards", to: "/menu", hint: "The dish list and the nutrient standard." },
  { id: "settings", label: "Settings", to: "/settings", hint: "Theme, accent, profile, goals." },
] as const;

export const TOTAL_AREAS = AREAS.length;

/** Route → area. Unknown paths fall back to home so the ring never stalls. */
export function areaForPath(pathname: string): AreaId {
  if (pathname.startsWith("/analyze")) return "analyze";
  if (pathname.startsWith("/result") || pathname.startsWith("/history")) return "history";
  if (pathname.startsWith("/analytics")) return "insights";
  if (pathname.startsWith("/students")) return "students";
  if (pathname.startsWith("/menu")) return "menu";
  if (pathname.startsWith("/settings")) return "settings";
  return "home";
}

/** Position in the nav order, used to pick the slide direction of a route. */
export function areaDepth(pathname: string): number {
  const id = areaForPath(pathname);
  const index = AREAS.findIndex((a) => a.id === id);
  return index < 0 ? 0 : index;
}

/* ------------------------------- badges ------------------------------- */

export type BadgeId =
  | "three-rooms"
  | "grand-tour"
  | "returning-visitor"
  | "night-shift"
  | "logo-patter"
  | "konami"
  | "nutri-whisper";

export interface Badge {
  id: BadgeId;
  label: string;
  /** The payoff text shown in the toast and the notebook. */
  note: string;
  points: number;
  /** Secret badges are hidden until found; only their riddle is shown. */
  secret: boolean;
  hint: string;
}

export const BADGES: readonly Badge[] = [
  {
    id: "three-rooms",
    label: "Three rooms",
    note: "You have seen Home, one data room and one tool. The rest of the map is drawn in the same ink.",
    points: 1,
    secret: false,
    hint: "Open any three sections.",
  },
  {
    id: "grand-tour",
    label: "Grand tour",
    note: "Every section visited. Nothing in this app is hidden behind a paywall — only behind curiosity.",
    points: 3,
    secret: false,
    hint: "Visit all seven sections.",
  },
  {
    id: "returning-visitor",
    label: "Second helping",
    note: "You came back on another day. The journal remembers what you measured.",
    points: 1,
    secret: false,
    hint: "Open the app on two different days.",
  },
  {
    id: "night-shift",
    label: "Night shift",
    note: "Some kitchens run after midnight. So does this one.",
    points: 1,
    secret: true,
    hint: "Wander in late at night.",
  },
  {
    id: "logo-patter",
    label: "Patter",
    note: "You drummed on the leaf mark five times. It has no function. That was the point.",
    points: 1,
    secret: true,
    hint: "Something in the corner answers to a tap — several, in fact.",
  },
  {
    id: "konami",
    label: "Old code",
    note: "Up, up, down, down… You remembered. So did we.",
    points: 2,
    secret: true,
    hint: "Some sequences never go out of style.",
  },
  {
    id: "nutri-whisper",
    label: "Nutri whisper",
    note: "Typed the first five letters anywhere on the page and the app listened.",
    points: 2,
    secret: true,
    hint: "Say the app's first five letters — outside any text field.",
  },
] as const;

export function badgeById(id: BadgeId): Badge {
  const found = BADGES.find((b) => b.id === id);
  if (!found) throw new Error(`unknown badge: ${id}`);
  return found;
}

export interface Level {
  name: string;
  index: number;
  /** Points still needed for the next level (null at the top level). */
  toNext: number | null;
}

const LEVELS = ["Taster", "Forager", "Explorer", "Cartographer"] as const;
const LEVEL_AT = [0, 2, 4, 7] as const;

export function levelFor(points: number): Level {
  let index = 0;
  for (let i = 0; i < LEVEL_AT.length; i++) if (points >= LEVEL_AT[i]) index = i;
  const next = LEVEL_AT[index + 1];
  return {
    name: LEVELS[index],
    index,
    toNext: next === undefined ? null : next - points,
  };
}

/* -------------------------------- state ------------------------------- */

export interface ExploreState {
  areas: AreaId[];
  badges: BadgeId[];
  /** Local calendar days (yyyy-mm-dd) the app was opened, capped. */
  days: string[];
}

const MAX_DAYS = 60;

export function emptyExploration(): ExploreState {
  return { areas: [], badges: [], days: [] };
}

export function pointsFor(state: ExploreState): number {
  return state.badges.reduce((sum, id) => sum + badgeById(id).points, 0);
}

export function exploredCount(state: ExploreState): number {
  return state.areas.length;
}

function localDay(now: Date): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Record a visit. Returns the SAME object when nothing changed, so callers
 * can skip a write (and StrictMode's double effect stays a no-op).
 */
export function recordVisit(state: ExploreState, area: AreaId, now: Date): ExploreState {
  const hasArea = state.areas.includes(area);
  const day = localDay(now);
  const hasDay = state.days.includes(day);
  if (hasArea && hasDay) return state;
  return {
    areas: hasArea ? state.areas : [...state.areas, area],
    badges: state.badges,
    days: hasDay ? state.days : [...state.days, day].slice(-MAX_DAYS),
  };
}

export function unlockBadge(state: ExploreState, id: BadgeId): ExploreState {
  if (state.badges.includes(id)) return state;
  return { ...state, badges: [...state.badges, id] };
}

/**
 * Apply the automatic rules that follow a visit. Secrets are never granted
 * here — they arrive through unlockBadge() from a deliberate interaction.
 */
export function settle(
  state: ExploreState,
  now: Date
): { state: ExploreState; unlocked: BadgeId[] } {
  const unlocked: BadgeId[] = [];
  let next = state;
  const grant = (id: BadgeId, when: boolean) => {
    if (!when || next.badges.includes(id)) return;
    next = { ...next, badges: [...next.badges, id] };
    unlocked.push(id);
  };
  const hour = now.getHours();
  grant("three-rooms", next.areas.length >= 3);
  grant("grand-tour", AREAS.every((a) => next.areas.includes(a.id)));
  grant("returning-visitor", next.days.length >= 2);
  grant("night-shift", hour >= 22 || hour < 5);
  return { state: next, unlocked };
}

/* ------------------------------ persistence --------------------------- */

function isAreaId(value: unknown): value is AreaId {
  return typeof value === "string" && AREAS.some((a) => a.id === value);
}

function isBadgeId(value: unknown): value is BadgeId {
  return typeof value === "string" && BADGES.some((b) => b.id === value);
}

/** Unknown/garbage ids are dropped, so a future rename can never crash boot. */
export function parseExploration(raw: string | null): ExploreState {
  if (!raw) return emptyExploration();
  try {
    const parsed = JSON.parse(raw) as Partial<Record<keyof ExploreState, unknown>>;
    const list = (v: unknown) => (Array.isArray(v) ? v : []);
    return {
      areas: list(parsed.areas).filter(isAreaId),
      badges: list(parsed.badges).filter(isBadgeId),
      days: list(parsed.days).filter((d): d is string => typeof d === "string").slice(-MAX_DAYS),
    };
  } catch {
    return emptyExploration();
  }
}

export function loadExploration(storage: Storage): ExploreState {
  return parseExploration(storage.get(EXPLORE_KEY));
}

export function saveExploration(storage: Storage, state: ExploreState): void {
  try {
    storage.set(EXPLORE_KEY, JSON.stringify(state));
  } catch {
    /* private-mode storage: exploration stays in memory for this session */
  }
}

/* ------------------------------ keystrokes ---------------------------- */

/** ↑ ↑ ↓ ↓ ← → ← → — matched as the tail of the keyboard history. */
const KONAMI = [
  "arrowup",
  "arrowup",
  "arrowdown",
  "arrowdown",
  "arrowleft",
  "arrowright",
  "arrowleft",
  "arrowright",
];

export const WHISPER = "nutri";

/**
 * Feed one keystroke through the secret detector. `buffer` is the caller's
 * recent-key tail; the return tells the caller which secret (if any) fired.
 */
export function detectSecret(
  buffer: string[],
  key: string
): { secret: BadgeId | null; buffer: string[] } {
  const k = key.toLowerCase();
  if (!/^([a-z]|arrow(up|down|left|right))$/.test(k)) return { secret: null, buffer };
  const tail = [...buffer, k].slice(-Math.max(KONAMI.length, WHISPER.length));
  if (KONAMI.every((expected, i) => tail[tail.length - KONAMI.length + i] === expected)) {
    return { secret: "konami", buffer: [] };
  }
  const letters = tail.filter((c) => c.length === 1).join("");
  if (letters.endsWith(WHISPER)) return { secret: "nutri-whisper", buffer: [] };
  return { secret: null, buffer: tail };
}
