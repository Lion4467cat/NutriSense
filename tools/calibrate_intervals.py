"""Interval calibration for learned-head grams — ticket 03, spec 002 decisions 7-9.

The per-class sigma in data/weight_head_sigma.yaml is a residual standard
deviation fitted on the whole DEV carve, so scoring calibration on the same
carve is in-sample. This tool measures calibration HONESTLY:

  * leave-one-PLATE-out over the 21 DEV plates (108 views / 1218 ROI
    samples): each fold refits ONLY the sigma/calibration layer on the 20
    in-fold plates — per-class residual std (>= min_count in-fold samples,
    else the file's full-DEV sigma; fallbacks counted) — and scores the
    held-out plate. The head checkpoint is NEVER retrained (WED train
    excludes the DEV plates): predictions come from the deployable path
    (WeightHead.load + tools/run_eval.score) computed once; every fold is
    array math on those fixed predictions.
  * nonconformity: |y - y_hat| / (Z90 * sigma_fold,class) — normalized
    residuals (the per-class sigma already makes nominal widths per-class).
  * Stage C: ONE global multiplier on the sigma layer (smallest grid T with
    pooled out-of-fold coverage_90 >= 0.90).
  * Stage B (pre-registered contingency, docs/ledger/004): if Stage C's
    smallest passing T exceeds the +25% width cap, per-class multipliers
    instead — each class calibrated by its own OOF scores with the same
    rule and grid; classes that cannot reach 0.90 within the grid get the
    grid ceiling and are flagged. Pooled OOF coverage is the gate; mean
    interval-width growth is sample-weighted (per-sample width ratio is
    exactly the class multiplier).
  * the wire interval (engine/mc.py lognormal central 90%, temperature 1.0)
    is checked out-of-fold at the same multiplier through the analytic
    lognormal quantiles of the fold's scaled sigma_rel — the gate is judged
    on the band shape (coverage_90 of record, run_eval semantics), the wire
    shape is reported alongside.

Landing (--apply): the multiplier(s) are written into the sigma artifact —
sigma_g and sigma_rel scaled per the deployed stage (the documented
sigma_rel = sigma_g / mean-GT invariant is preserved at the calibrated
scale), _meta.calibration carries provenance, status: calibrated (like
ticket 02's threshold). temperature_scale stays 1.0: one calibration,
applied once. The checkpoint is untouched; wire interval semantics are
unchanged (interval_90 gets honest widths through the existing sigma -> MC
seam). Re-applying is refused: a re-calibration after a retrain is a
deliberate re-run of this ticket, not a flag.

Width cap (pre-registered): mean interval width growth <= +25% — above it
the stage FAILS and is investigated, not shipped. No LOCKED access anywhere
in this tool (DEV rows only).

Run:
  .venv/bin/python -m tools.calibrate_intervals                # measure + report
  .venv/bin/python -m tools.calibrate_intervals --apply        # land the artifact
  .venv/bin/python -m tools.calibrate_intervals --limit 3      # smoke
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SIGMA_PATH = _ROOT / "data" / "weight_head_sigma.yaml"
REPORT_PATH = _ROOT / "data" / "reports" / "interval_calibration.json"

Z90 = 1.6448536269514722          # two-sided 90% normal quantile (run_eval's)
ALPHA = 0.10                      # nominal miss probability
MIN_FOLD_COUNT = 3                # mirrors train_weight_head's sigma-writing rule
GRID_LO, GRID_HI, GRID_STEP = 0.50, 1.50, 0.005
WIDTH_CAP = 0.25                  # +25% mean width growth — pre-registered cap
TICKET = "03-interval-calibration"
LEDGER = "004"


# ---------------------------------------------------------------- conformal --
def conformal_quantile(scores, alpha: float = ALPHA) -> float:
    """Split-conformal quantile: the k-th smallest calibration score with
    k = ceil((1 - alpha) * (n + 1)) (finite-sample correction, 1-indexed);
    P(score_new <= q) >= 1 - alpha under exchangeability."""
    s = np.sort(np.asarray(scores, dtype=float))
    n = s.size
    if n == 0:
        raise ValueError("no calibration scores")
    k = min(int(math.ceil((1.0 - alpha) * (n + 1))), n)
    return float(s[k - 1])


def choose_multiplier(scores, target: float = 1.0 - ALPHA,
                      lo: float = GRID_LO, hi: float = GRID_HI,
                      step: float = GRID_STEP) -> float | None:
    """Smallest grid multiplier whose coverage reaches `target` (the
    pre-registered selection rule). None if the grid is exhausted."""
    scores = np.asarray(scores, dtype=float)
    t = lo
    while t <= hi + 1e-9:
        if float(np.mean(scores <= t)) >= target:
            return round(t, 4)
        t = round(t + step, 4)
    return None


def coverage_at(scores, t: float) -> float:
    return float(np.mean(np.asarray(scores, dtype=float) <= t))


# -------------------------------------------------------------------- folds --
def fold_sigma_refit(infold, file_sigma_g: dict[str, float],
                     file_sigma_rel: dict[str, float],
                     min_count: int = MIN_FOLD_COUNT
                     ) -> tuple[dict[str, float], dict[str, float], int]:
    """One fold's sigma layer: per-class residual std (+ sigma_rel = sigma /
    mean GT, max(1, mean) floor — the file's own construction) over the
    in-fold samples; classes with < min_count in-fold residuals fall back to
    the file's full-DEV sigma (sample count returned). infold: sample dicts."""
    by_class: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for s in infold:
        by_class[s["dish"]].append((s["pred"], s["gt"]))
    sigma_g: dict[str, float] = {}
    sigma_rel: dict[str, float] = {}
    fallback = 0
    for dish, pairs in by_class.items():
        if len(pairs) >= min_count:
            res = np.array([p - g for p, g in pairs], dtype=float)
            gts = np.array([g for _, g in pairs], dtype=float)
            sg = float(np.std(res))
            sigma_g[dish] = sg
            sigma_rel[dish] = sg / max(1.0, float(gts.mean()))
        else:
            if dish not in file_sigma_g:
                raise KeyError(f"no sigma for dish {dish!r} in the artifact")
            sigma_g[dish] = float(file_sigma_g[dish])
            sigma_rel[dish] = float(file_sigma_rel.get(dish, 0.30))
            fallback += len(pairs)
    return sigma_g, sigma_rel, fallback


def normalized_scores(samples, sigma_g: dict[str, float]) -> np.ndarray:
    """|y - y_hat| / (Z90 * sigma_class) — raises if a sample's dish has no
    sigma (the DEV carve must be fully covered by the artifact)."""
    out = np.empty(len(samples), dtype=float)
    for i, s in enumerate(samples):
        dish = s["dish"]
        if dish not in sigma_g:
            raise KeyError(f"sample dish {dish!r} has no sigma entry")
        out[i] = abs(s["gt"] - s["pred"]) / (Z90 * sigma_g[dish])
    return out


def wire_interval(pred: float, sigma_rel: float) -> tuple[float, float]:
    """engine/mc.py wire interval at temperature 1.0: samples are
    pred * lognormal(mean 1, s); the central 90% interval is the analytic
    p05/p95 of that lognormal (median pred * exp(-s^2/2))."""
    s = float(sigma_rel)
    lo = pred * math.exp(-0.5 * s * s - Z90 * s)
    hi = pred * math.exp(-0.5 * s * s + Z90 * s)
    return lo, hi


def wire_width_rel(sigma_rel: float) -> float:
    """Analytic lognormal central-90% width per gram of prediction."""
    s = float(sigma_rel)
    return math.exp(-0.5 * s * s) * (math.exp(Z90 * s) - math.exp(-Z90 * s))


def read_sigma_doc(path: Path = SIGMA_PATH) -> dict:
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict) or "sigma_g" not in doc:
        raise ValueError(f"{path}: no sigma_g block")
    return doc


# --------------------------------------------------------------- stage fits --
def _stage_c(oof_scores: np.ndarray, per_class_idx: dict[str, list[int]]) -> dict:
    t = choose_multiplier(oof_scores)
    out: dict = {"stage": "C", "multiplier": t}
    if t is None:
        out.update({"oof_coverage_90_band": None, "oof_coverage_90_wire": None,
                    "band_width_growth_pct": None,
                    "gate": {"oof_coverage_90_ge_0.90": False,
                             "width_growth_le_25pct": False}})
        return out
    band = round(coverage_at(oof_scores, t), 4)
    out.update({
        "oof_coverage_90_band": band,
        "band_width_growth_pct": round(100.0 * (t - 1.0), 2),
        "gate": {"oof_coverage_90_ge_0.90": band >= 0.90,
                 "width_growth_le_25pct": t - 1.0 <= WIDTH_CAP}})
    return out


def _stage_b(oof_scores: np.ndarray, per_class_idx: dict[str, list[int]]) -> dict:
    """Per-class multipliers (pre-registered contingency): each class gets
    the smallest grid T reaching 0.90 on its OWN OOF scores; classes that
    cannot reach it within the grid get the grid ceiling and are flagged.
    Mean width growth is sample-weighted (per-sample width ratio == T)."""
    t_cls: dict[str, float] = {}
    capped: list[str] = []
    for dish, idx in per_class_idx.items():
        t = choose_multiplier(oof_scores[idx])
        if t is None:
            t = GRID_HI
            capped.append(dish)
        t_cls[dish] = t
    flags = np.array([oof_scores[j] <= t_cls[dish]
                      for dish, idx in per_class_idx.items()
                      for j in idx], dtype=bool)
    pooled = round(float(flags.mean()), 4)
    growth = round(100.0 * (float(np.mean([t_cls[d] for d, idx in
                                           per_class_idx.items()
                                           for _ in idx])) - 1.0), 2)
    out = {
        "stage": "B", "multiplier_per_class": t_cls,
        "oof_coverage_90_band": pooled,
        "band_width_growth_pct": growth,
        "classes_capped_at_grid_ceiling": capped,
        "gate": {"oof_coverage_90_ge_0.90": pooled >= 0.90,
                 "width_growth_le_25pct": growth <= 100.0 * WIDTH_CAP}}
    return out


def calibrate(samples, file_sigma_g: dict[str, float],
              file_sigma_rel: dict[str, float]) -> dict:
    """The full leave-one-plate-out measurement. Returns the report body:
    machinery stats, both pre-registered stages, and the deployed layer
    (Stage C if its gate passes, else Stage B, else None)."""
    plates = sorted({s["plate"] for s in samples})
    n = len(samples)
    by_plate: dict[str, list[int]] = defaultdict(list)
    for j, s in enumerate(samples):
        by_plate[s["plate"]].append(j)

    oof_scores = np.empty(n, dtype=float)       # fold-refit-sigma scores
    oof_covered_proc = np.zeros(n, dtype=bool)  # per-fold-conformal procedure
    fallback_by_sample = np.zeros(n, dtype=int)
    fold_sig_rel: list[dict[str, float]] = [dict(file_sigma_rel)
                                            for _ in plates]
    per_fold: list[dict] = []

    for i, plate in enumerate(plates):
        held = by_plate[plate]
        infold = [samples[j] for j in range(n) if j not in set(held)]
        sig_g_f, sig_rel_f, fb = fold_sigma_refit(infold, file_sigma_g,
                                                  file_sigma_rel)
        fold_sig_rel[i] = sig_rel_f
        held_samples = [samples[j] for j in held]
        held_scores = normalized_scores(held_samples, sig_g_f)
        oof_scores[held] = held_scores
        fallback_by_sample[held] = fb
        c_f = conformal_quantile(held_scores)
        oof_covered_proc[held] = held_scores <= c_f
        per_fold.append({
            "plate": plate, "n_held": len(held), "fallback_samples": fb,
            "fold_conformal_multiplier": round(c_f, 4),
            "fold_heldout_coverage_at_c_f":
                round(float(np.mean(held_scores <= c_f)), 4)})

    per_class_idx: dict[str, list[int]] = {}
    for j, s in enumerate(samples):
        per_class_idx.setdefault(s["dish"], []).append(j)

    # corroboration: the full-DEV split-conformal quantile on file-sigma scores
    full_scores = normalized_scores(samples, file_sigma_g)
    t_conf = conformal_quantile(full_scores)

    curve = []
    t = GRID_LO
    while t <= GRID_HI + 1e-9:
        curve.append((round(t, 4), round(coverage_at(oof_scores, t), 4)))
        t = round(t + GRID_STEP, 4)

    # ---- wire-shape OOF at a deployed layer (shared by both stages) ----
    def wire_oof_at(t_per_class: dict[str, float]) -> tuple[float, float]:
        flags = np.zeros(n, dtype=bool)
        ratios: list[float] = []
        for i, plate in enumerate(plates):
            for j in by_plate[plate]:
                s = samples[j]
                dish = s["dish"]
                s_rel = fold_sig_rel[i][dish] * t_per_class[dish]
                lo, hi = wire_interval(s["pred"], s_rel)
                flags[j] = lo <= s["gt"] <= hi
                ratios.append(wire_width_rel(s_rel)
                              / wire_width_rel(fold_sig_rel[i][dish]))
        return round(float(flags.mean()), 4), \
            round(100.0 * (float(np.mean(ratios)) - 1.0), 2)

    sc = _stage_c(oof_scores, per_class_idx)
    if sc["multiplier"] is not None:
        w_cov, w_grow = wire_oof_at({d: sc["multiplier"]
                                     for d in per_class_idx})
        sc["oof_coverage_90_wire"] = w_cov
        sc["wire_width_growth_pct"] = w_grow
    sb = _stage_b(oof_scores, per_class_idx)
    w_cov, w_grow = wire_oof_at(sb["multiplier_per_class"])
    sb["oof_coverage_90_wire"] = w_cov
    sb["wire_width_growth_pct"] = w_grow

    if sc["gate"]["oof_coverage_90_ge_0.90"] and \
            sc["gate"]["width_growth_le_25pct"]:
        deployed_stage, layer = "C", sc
    elif sb["gate"]["oof_coverage_90_ge_0.90"] and \
            sb["gate"]["width_growth_le_25pct"]:
        deployed_stage, layer = "B", sb
    else:
        deployed_stage, layer = None, None

    per_class = {}
    for dish, idx in per_class_idx.items():
        per_class[dish] = {
            "n": len(idx),
            "fallback_samples": int(fallback_by_sample[idx].sum())}
        for stage_name, stage in (("C", sc), ("B", sb)):
            if stage_name == "C":
                t_ref = stage.get("multiplier")
                if t_ref is None:
                    t_ref = GRID_HI  # report coverage at the widest allowed T
            else:
                t_ref = stage["multiplier_per_class"][dish]
            cov = round(coverage_at(oof_scores[idx], t_ref), 4)
            per_class[dish][f"oof_coverage_90_{stage_name.lower()}"] = cov
    spread = [v["oof_coverage_90_c"] for v in per_class.values()]

    return {
        "ticket": TICKET, "ledger_entry": LEDGER,
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "n_samples": n, "n_plates": len(plates), "n_folds": len(plates),
        "alpha": ALPHA, "z90": round(Z90, 6),
        "min_fold_count": MIN_FOLD_COUNT,
        "grid": {"lo": GRID_LO, "hi": GRID_HI, "step": GRID_STEP},
        "nominal_check": {
            "oof_coverage_90_band_at_multiplier_1.0":
                round(coverage_at(oof_scores, 1.0), 4),
            "full_dev_band_coverage_90_at_file_sigma":
                round(float(np.mean(full_scores <= 1.0)), 4),
            "full_dev_split_conformal_quantile": round(t_conf, 4),
            "full_dev_coverage_90_at_conformal_quantile":
                round(float(np.mean(full_scores <= t_conf)), 4),
        },
        "per_fold": per_fold,
        "per_fold_procedure_pooled_oof_coverage_90":
            round(float(np.mean(oof_covered_proc)), 4),
        "stage_c": sc, "stage_b": sb,
        "deployed_stage": deployed_stage,
        "deployed_multiplier": layer["multiplier"] if layer else None,
        "deployed_multiplier_per_class":
            layer.get("multiplier_per_class") if layer else None,
        "oof_coverage_90_band": layer["oof_coverage_90_band"] if layer else None,
        "oof_coverage_90_wire": layer["oof_coverage_90_wire"] if layer else None,
        "band_width_growth_pct":
            layer["band_width_growth_pct"] if layer else None,
        "wire_width_growth_pct":
            layer.get("wire_width_growth_pct") if layer else None,
        "fallback_samples_total": int(fallback_by_sample.sum()),
        "fallback_fraction": round(float(fallback_by_sample.mean()), 4),
        "per_class": per_class,
        "per_class_spread": {"min": round(min(spread), 4),
                             "mean": round(float(np.mean(spread)), 4),
                             "max": round(max(spread), 4)},
        "oof_curve": curve,
    }


def apply_calibration(stage_c_multiplier: float | None,
                      stage_b_multipliers: dict[str, float] | None,
                      report_path: str, oof_band: float, oof_wire: float,
                      nominal_dev: float,
                      sigma_path: Path = SIGMA_PATH) -> dict:
    """Land the deployed stage's multipliers on the sigma artifact with
    provenance. Refuses an already-calibrated file (a retrain wipes the
    calibration block — re-run this ticket deliberately after any retrain)."""
    doc = read_sigma_doc(sigma_path)
    meta = doc.setdefault("_meta", {})
    if "calibration" in meta:
        raise ValueError(
            f"{sigma_path}: already carries _meta.calibration (multiplier "
            f"{meta['calibration'].get('multiplier')}) — recalibration is a "
            "deliberate re-run of ticket 03")
    t_map: dict[str, float]
    if stage_c_multiplier is not None:
        if stage_b_multipliers is not None:
            raise ValueError("exactly one of stage C / stage B multipliers")
        t_map = {k: stage_c_multiplier for k in doc["sigma_g"]}
        stage = "C"
    else:
        if stage_b_multipliers is None:
            raise ValueError("exactly one of stage C / stage B multipliers")
        t_map = stage_b_multipliers
        stage = "B"
    doc["sigma_g"] = {k: round(float(v) * t_map[k], 2)
                      for k, v in doc["sigma_g"].items()}
    doc["sigma_rel"] = {k: round(float(v) * t_map[k], 4)
                        for k, v in doc["sigma_rel"].items()}
    meta["calibration"] = {
        "stage": stage,
        "multiplier": (float(stage_c_multiplier)
                       if stage_c_multiplier is not None else None),
        "multiplier_per_class": (None if stage_c_multiplier is not None
                                 else {k: float(v) for k, v in t_map.items()}),
        "calibrated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "method": "split-conformal normalized residuals |y-pred|/(Z90*sigma), "
                  "leave-one-plate-out over the 21 DEV plates (fold-refit "
                  "sigma layer, head never retrained), "
                  + ("one global multiplier" if stage == "C"
                     else "per-class multipliers"),
        "status": "calibrated",
        "oof_coverage_90_band": oof_band,
        "oof_coverage_90_wire": oof_wire,
        "nominal_dev_coverage_90": nominal_dev,
        "source_report": report_path,
        "ticket": f"{TICKET} (ledger {LEDGER})",
    }
    doc["note"] = (
        "per-class 90% interval widths for the learned head: residual std on "
        "the carved val split (deployable path, WeightHead.load) TIMES the "
        "split-conformal multiplier(s) in _meta.calibration — one global "
        "value (stage C) or per-class (stage B) (raw residual std ~= value / "
        "multiplier); sigma_rel = sigma_g / mean GT grams on the same split "
        "at the calibrated scale; feeds the MC lognormal grams sigma in "
        "engine/mc.py (learned path) and the tools/run_eval coverage band; "
        "temperature_scale stays 1.0 (one calibration, applied once)")
    sigma_path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return meta["calibration"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default="dev", choices=("dev",),
                    help="DEV only — the only tuning tier (docs/eval_protocol.md)")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="smoke only")
    ap.add_argument("--report-out", default=str(REPORT_PATH))
    ap.add_argument("--sigma-out", default=str(SIGMA_PATH))
    ap.add_argument("--apply", action="store_true",
                    help="land the deployed stage's multipliers on the sigma "
                         "artifact (provenance)")
    args = ap.parse_args(argv)
    t0 = time.time()

    import torch
    from models.weight_head import WeightHead
    from tools.run_eval import dev_rows, score, wed_root

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    rows = dev_rows()
    if args.limit is not None:
        rows = rows[:args.limit]
    model = WeightHead.load(_ROOT / "data" / "weight_head.pt", device=device)
    samples = score(model, rows, wed_root(), device, batch=args.batch)

    doc = read_sigma_doc(Path(args.sigma_out))
    file_sigma_g = {k: float(v) for k, v in doc["sigma_g"].items()}
    file_sigma_rel = {k: float(v) for k, v in doc["sigma_rel"].items()}
    missing = sorted({s["dish"] for s in samples} - set(file_sigma_g))
    if missing:
        raise RuntimeError(f"dishes without a sigma entry: {missing} — the "
                           "DEV carve must be fully covered")

    rep = calibrate(samples, file_sigma_g, file_sigma_rel)
    rep.update({"tier": args.tier, "limit": args.limit,
                "checkpoint": "data/weight_head.pt",
                "checkpoint_meta": getattr(model, "meta", {}),
                "device": str(device), "applied": False})

    print(f"tier={args.tier} samples={rep['n_samples']} "
          f"plates={rep['n_plates']} folds={rep['n_folds']}", flush=True)
    print(f"tier={args.tier} nominal: oof_band_cov@1.0="
          f"{rep['nominal_check']['oof_coverage_90_band_at_multiplier_1.0']} "
          f"full_dev_cov@file_sigma="
          f"{rep['nominal_check']['full_dev_band_coverage_90_at_file_sigma']} "
          f"full_dev_conformal_quantile="
          f"{rep['nominal_check']['full_dev_split_conformal_quantile']}",
          flush=True)
    print(f"tier={args.tier} per-fold-procedure pooled OOF coverage="
          f"{rep['per_fold_procedure_pooled_oof_coverage_90']}", flush=True)
    for name in ("stage_c", "stage_b"):
        s = rep[name]
        if s.get("multiplier") is not None:
            t_txt = str(s["multiplier"])
        else:
            t = s.get("multiplier_per_class") or {}
            t_txt = (f"{len(t)} per-class (capped: "
                     f"{len(s['classes_capped_at_grid_ceiling'])})")
        print(f"tier={args.tier} {name}: T={t_txt} "
              f"oof_band={s['oof_coverage_90_band']} "
              f"oof_wire={s['oof_coverage_90_wire']} "
              f"band_growth={s['band_width_growth_pct']}% "
              f"wire_growth={s.get('wire_width_growth_pct')}% "
              f"gate={s['gate']}", flush=True)
    print(f"tier={args.tier} deployed_stage={rep['deployed_stage']} "
          f"band_growth={rep['band_width_growth_pct']}% "
          f"wire_growth={rep['wire_width_growth_pct']}%", flush=True)
    print(f"tier={args.tier} fallback_samples={rep['fallback_samples_total']} "
          f"({rep['fallback_fraction']}) per_class_spread="
          f"{rep['per_class_spread']}", flush=True)

    if args.apply:
        if rep["deployed_stage"] is None:
            raise RuntimeError(
                "neither stage passes the pre-registered gate — not applying "
                "(Stage C width cap + Stage B failure: see the report)")
        if rep["deployed_stage"] == "C":
            cal = apply_calibration(rep["deployed_multiplier"], None,
                                    args.report_out,
                                    rep["oof_coverage_90_band"],
                                    rep["oof_coverage_90_wire"],
                                    rep["nominal_check"]
                                    ["full_dev_band_coverage_90_at_file_sigma"],
                                    Path(args.sigma_out))
        else:
            cal = apply_calibration(None, rep["deployed_multiplier_per_class"],
                                    args.report_out,
                                    rep["oof_coverage_90_band"],
                                    rep["oof_coverage_90_wire"],
                                    rep["nominal_check"]
                                    ["full_dev_band_coverage_90_at_file_sigma"],
                                    Path(args.sigma_out))
        rep["applied"] = True
        rep["applied_to"] = args.sigma_out
        print(f"tier={args.tier} applied stage {cal['stage']} "
              f"-> {args.sigma_out}", flush=True)

    rep["wall_s"] = round(time.time() - t0, 2)
    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2) + "\n")
    print(f"tier={args.tier} wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
