import type { ReactNode } from "react";
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
