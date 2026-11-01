import { verdictMeta } from "./verdicts";

export function VerdictPill({ verdict }: { verdict: string }) {
  const m = verdictMeta(verdict);
  const VerdictIcon = m.icon;
  return (
    <span className={`pill ${m.cls}`} role="status">
      <span className="pill-ico" aria-hidden="true">
        <VerdictIcon size={14} />
      </span>
      {m.label}
    </span>
  );
}
