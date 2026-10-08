import type { ReactNode } from "react";
import type { Verdict } from "../types/api";

/* ---------------- verdict helpers ---------------- */

export interface VerdictMeta {
  key: Verdict;
  label: string;
  icon: string;
  cls: "pass" | "warn" | "fail" | "neutral";
  blurb: string;
}

export const VERDICT_META: Record<Verdict, VerdictMeta> = {
  PASS: {
    key: "PASS",
    label: "PASS",
    icon: "✓",
    cls: "pass",
    blurb: "Meal meets the required nutrition threshold with sufficient coverage.",
  },
  BORDERLINE: {
    key: "BORDERLINE",
    label: "BORDERLINE",
    icon: "!",
    cls: "warn",
    blurb: "Probabilities are close to a threshold, or coverage is short of the gate.",
  },
  FAIL: {
    key: "FAIL",
    label: "FAIL",
    icon: "✕",
    cls: "fail",
    blurb: "Mandatory nutrition is below the required minimum with sufficient coverage.",
  },
  cannot_verify: {
    key: "cannot_verify",
    label: "CANNOT VERIFY",
    icon: "?",
    cls: "neutral",
    blurb: "The capture could not be verified — check capture quality and try again.",
  },
  out_of_scope: {
    key: "out_of_scope",
    label: "OUT OF SCOPE",
    icon: "–",
    cls: "warn",
    blurb: "This item is not portion-scored under PM POSHAN compliance.",
  },
};

export function verdictMeta(v: string | undefined | null): VerdictMeta {
  return VERDICT_META[(v as Verdict) || "cannot_verify"] ?? VERDICT_META.cannot_verify;
}

export function VerdictPill({ verdict }: { verdict: string }) {
  const m = verdictMeta(verdict);
  return (
    <span className={`pill ${m.cls}`} role="status">
      <span className="pill-ico" aria-hidden="true">
        {m.icon}
      </span>
      {m.label}
    </span>
  );
}

/* ---------------- empty state ---------------- */

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon" aria-hidden="true">
        {icon}
      </span>
      <h3>{title}</h3>
      {children ? <p>{children}</p> : null}
      {action}
    </div>
  );
}

/* ---------------- card ---------------- */

export function Card({
  title,
  sub,
  action,
  children,
  pad = true,
  className = "",
}: {
  title?: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  pad?: boolean;
  className?: string;
}) {
  return (
    <section className={`card ${pad ? "card-pad" : ""} ${className}`}>
      {(title || action) && (
        <div className="card-head">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {sub && <p className="card-sub">{sub}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/* ---------------- status mark ---------------- */

export function StatusMark({ level }: { level: "good" | "warn" | "bad" | "idle" }) {
  const glyph = level === "good" ? "✓" : level === "warn" ? "!" : level === "bad" ? "✕" : "·";
  const text =
    level === "good" ? "Good" : level === "warn" ? "Attention" : level === "bad" ? "Invalid" : "Unknown";
  return (
    <span className={`s-mark ${level}`} title={text} aria-label={text}>
      {glyph}
    </span>
  );
}

/* ---------------- section collapse ---------------- */

export function Collapse({
  summary,
  meta,
  children,
  defaultOpen = false,
  className = "",
}: {
  summary: ReactNode;
  meta?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  return (
    <details className={`collapse ${className}`} open={defaultOpen}>
      <summary>
        {summary}
        {meta && <span className="tag">{meta}</span>}
        <svg
          className="chev"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="m6 9.5 6 6 6-6" />
        </svg>
      </summary>
      <div className="collapse-body">{children}</div>
    </details>
  );
}
