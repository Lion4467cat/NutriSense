import type { AnalyzeResult } from  "../types/api";
import { Card, StatusMark } from  "../ui/primitives";

interface Row {
  name: string;
  level: "good" | "warn" | "bad" | "idle";
  value: string;
}

export default function CaptureQuality({ result }: { result: AnalyzeResult }) {
  const lint = result.lint;
  const rows: Row[] = [];

  if (lint) {
    const zoom = lint.digital_zoom;
    rows.push({
      name: "Digital zoom",
      level: zoom == null ? "idle" : zoom === 1 ? "good" : "bad",
      value: zoom == null ? "not reported" : String(zoom),
    });
    rows.push({
      name: "Resolution",
      level: lint.resolution_ok ? "good" : "warn",
      value: `${lint.min_side_px}px min side${lint.resolution_ok ? "" : " (below 1280)"}`,
    });
  }

  const anchor = result.anchor;
  rows.push({
    name: "Reference marker",
    level: anchor ? (anchor.tier === "measured" ? "good" : "warn") : "idle",
    value: anchor
      ? anchor.tier === "measured"
        ? `${anchor.method}`
        : "prior tier — no marker"
      : "not assessed",
  });

  const flags = result.portion?.flags || [];
  rows.push({
    name: "Portion flags",
    level: flags.length === 0 ? "good" : "warn",
    value: flags.length === 0 ? "none" : flags.join(", "),
  });

  rows.push({
    name: "On-day menu",
    level: result.dish ? (result.dish.on_day ? "good" : "warn") : "idle",
    value: result.dish
      ? result.dish.on_day
        ? `${result.dish.display_name} served this day`
        : `${result.dish.display_name} is off-menu today`
      : "unknown",
  });

  rows.push({
    name: "Capture validity",
    level:
      result.verdict === "cannot_verify"
        ? "bad"
        : lint?.notes?.length
          ? "warn"
          : "good",
    value:
      result.verdict === "cannot_verify"
        ? "capture not verifiable"
        : lint?.notes?.length
          ? `${lint.notes.length} note${lint.notes.length > 1 ? "s" : ""}`
          : "clean",
  });

  return (
    <Card
      title="Capture quality"
      sub="Only values returned by the backend — no invented indicators."
    >
      {rows.map((r) => (
        <div className="status-row" key={r.name}>
          <StatusMark level={r.level} />
          <span className="sr-name">{r.name}</span>
          <span className="sr-val">{r.value}</span>
        </div>
      ))}
      {lint?.notes && lint.notes.length > 0 && (
        <>
          {lint.notes.map((n, i) => (
            <div className="banner warn" style={{ marginTop: 10 }} key={i}>
              <span aria-hidden="true">!</span>
              <div>{n}</div>
            </div>
          ))}
        </>
      )}
    </Card>
  );
}
