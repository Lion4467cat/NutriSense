import { verdictMeta } from "./verdicts";

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
