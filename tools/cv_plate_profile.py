"""Plate-level cross-validation spread profile of the deployed weight head.

Ticket 06, spec 002 decision 11 — measurement-only (ledger 005). Ledger
004 found the interval-calibration defect is NOT a width defect but a
point-estimate defect: whole plates are systematically mis-predicted
(per-plate mean standardized residual std 0.700 vs 0.131 iid; 81% of the
>1.5sigma tail on biased plates; worst plate 20250517_set30 beans-curry
predicted 60-77 g vs GT 300 g on all 5 views). This tool quantifies where
the DEV error mass lives:

  * per-plate MAE, signed mean error, share of total absolute error, and
    the top-k cumulative concentration vs the uniform share;
  * per-sample standardized residuals (signed err / fold-refit per-class
    sigma, ticket-03 leave-one-plate-out machinery imported — not copied)
    with per-plate means, their cross-plate std, and the iid expectation
    sqrt(mean_j(1/n_j));
  * the plate jackknife: overall error recomputed with each plate
    excluded one at a time (who inflates / deflates the headline);
  * the OOF band coverage at nominal T = 1.0 — reproduced from ledger
    004 (0.8103) as the machinery cross-check;
  * per-dish signed-error table and per-view detail for the worst
    plate-dish cells.

The full per-sample table (plate, dish, pred, gt, err) is saved in the
report so every number is re-derivable. Nothing is trained, nothing
lands: the checkpoint, sigma file and all protected paths are untouched.

Run:
  .venv/bin/python -m tools.cv_plate_profile
  .venv/bin/python -m tools.cv_plate_profile --limit 3   # smoke
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

REPORT_PATH = _ROOT / "data" / "reports" / "cv_plate_profile.json"
TICKET = "06-robustness-program"
LEDGER = "005"
EXPECTED_MAE_G = 15.034        # ledger-003 keep run (data/reports/...)
EXPECTED_OOF_T1 = 0.8103       # ledger-004 nominal OOF band coverage at T=1.0


def overall_mae(samples: list[dict]) -> float:
    return float(np.mean([abs(s["err"]) for s in samples]))


def plate_table(samples: list[dict]) -> list[dict]:
    """Per-plate aggregates sorted by absolute-error share, DESC."""
    by: dict[str, list[float]] = defaultdict(list)
    signed: dict[str, list[float]] = defaultdict(list)
    for s in samples:
        by[s["plate"]].append(abs(s["err"]))
        signed[s["plate"]].append(s["err"])
    total = float(sum(abs(s["err"]) for s in samples))
    rows = []
    for plate in sorted(by):
        rows.append({
            "plate": plate,
            "n": len(by[plate]),
            "mae": float(np.mean(by[plate])),
            "abs_err": float(sum(by[plate])),
            "share": float(sum(by[plate])) / total if total else 0.0,
            "mean_err": float(np.mean(signed[plate])),
        })
    rows.sort(key=lambda r: (-r["abs_err"], r["plate"]))
    return rows


def dish_table(samples: list[dict]) -> list[dict]:
    """Per-dish MAE + signed mean error, sorted by absolute error DESC."""
    by: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by[s["dish"]].append(s)
    rows = []
    for dish in sorted(by):
        errs = [s["err"] for s in by[dish]]
        rows.append({
            "dish": dish,
            "n": len(errs),
            "mae": round(float(np.mean(np.abs(errs))), 3),
            "mean_err": round(float(np.mean(errs)), 3),
            "abs_err": round(float(np.sum(np.abs(errs))), 3),
        })
    rows.sort(key=lambda r: (-r["mae"], r["dish"]))
    return rows


def concentration(rows: list[dict], k: int) -> dict:
    """Fraction of total absolute error held by the k worst plates vs the
    uniform (error-spread-evenly-over-plates) benchmark k/n_plates."""
    top_k = float(sum(r["abs_err"] for r in rows[:k]))
    total = float(sum(r["abs_err"] for r in rows))
    n = len(rows)
    return {"k": k, "share": round(top_k / total, 4) if total else 0.0,
            "uniform_share": round(k / n, 4) if n else 0.0}


def gini(rows: list[dict]) -> float:
    """Gini coefficient of the per-plate absolute-error mass (0 = equal)."""
    v = np.sort(np.array([r["abs_err"] for r in rows], dtype=float))
    n = v.size
    if n == 0 or v.sum() == 0:
        return 0.0
    cum = np.cumsum(v)
    return round(float((n + 1 - 2 * (cum / cum[-1]).sum()) / n), 4)


def jackknife(samples: list[dict]) -> list[dict]:
    """Plate jackknife: overall |err| mean with each plate excluded one at
    a time; delta = (MAE without the plate) - (MAE over all samples)."""
    overall = overall_mae(samples)
    out = []
    for plate in sorted({s["plate"] for s in samples}):
        kept = [abs(s["err"]) for s in samples if s["plate"] != plate]
        mae_wo = float(np.mean(kept))
        out.append({"plate": plate, "n_excluded": len(
            [1 for s in samples if s["plate"] == plate]),
            "mae_without_g": round(mae_wo, 4),
            "delta_g": round(mae_wo - overall, 4)})
    out.sort(key=lambda r: r["delta_g"])
    return out


def oof_coverage_profile(samples: list[dict],
                         file_sigma_g: dict[str, float],
                         file_sigma_rel: dict[str, float]) -> dict:
    """Ticket-03 machinery on the same samples: LOPO fold-refit sigma ->
    pooled OOF band coverage at T = 1.0 (nominal machinery cross-check),
    plus signed standardized residuals (err / fold sigma per class) and
    per-plate means of them with their cross-plate std vs the iid
    expectation sqrt(mean_j(1/n_j))."""
    from tools.calibrate_intervals import fold_sigma_refit, normalized_scores

    plates = sorted({s["plate"] for s in samples})
    n = len(samples)
    by_plate: dict[str, list[int]] = defaultdict(list)
    for j, s in enumerate(samples):
        by_plate[s["plate"]].append(j)

    oof_scores = np.empty(n, dtype=float)     # |err| / (Z90 * fold sigma)
    oof_refl = np.empty(n, dtype=bool)
    std_res = np.empty(n, dtype=float)        # signed err / fold sigma
    for i, plate in enumerate(plates):
        held = by_plate[plate]
        infold = [samples[j] for j in range(n) if j not in set(held)]
        sig_g_f, _sig_rel_f, _fb = fold_sigma_refit(infold, file_sigma_g,
                                                    file_sigma_rel)
        held_samples = [samples[j] for j in held]
        oof_scores[held] = normalized_scores(held_samples, sig_g_f)
        fold_sig = np.array([sig_g_f[s["dish"]] for s in held_samples],
                            dtype=float)
        signed = np.array([s["err"] for s in held_samples], dtype=float)
        std_res[held] = signed / fold_sig
    from tools.calibrate_intervals import conformal_quantile
    for i, plate in enumerate(plates):
        held = by_plate[plate]
        c_f = conformal_quantile(oof_scores[held])
        oof_refl[held] = oof_scores[held] <= c_f

    plate_rows = []
    for i, plate in enumerate(plates):
        idx = by_plate[plate]
        plate_rows.append({
            "plate": plate,
            "n": len(idx),
            "mean_std_resid": round(float(np.mean(std_res[idx])), 4),
        })
    means = np.array([r["mean_std_resid"] for r in plate_rows])
    n_arr = np.array([len(by_plate[p]) for p in plates], dtype=float)
    biased_flags = np.abs(means) > 0.3
    n_biased_samples = int(sum(len(by_plate[p]) for i, p in enumerate(plates)
                               if biased_flags[i]))
    tail_on_biased, tail_total = 0, 0
    for i, plate in enumerate(plates):
        idx = by_plate[plate]
        tail = np.abs(std_res[idx]) > 1.5
        tail_total += int(tail.sum())
        if biased_flags[i]:
            tail_on_biased += int(tail.sum())
    frac_biased = (tail_on_biased / tail_total) if tail_total else 0.0
    return {
        "pooled_oof_coverage_90_band_at_t_1_0":
            round(float(np.mean(oof_scores <= 1.0)), 4),
        "pooled_oof_coverage_90_per_fold_procedure":
            round(float(np.mean(oof_refl)), 4),
        "iid_expected_std_of_plate_mean_std_resid":
            round(float(np.sqrt(np.mean(1.0 / n_arr))), 4),
        "plate_mean_std_resid_std": round(float(np.std(means)), 4),
        "frac_samples_on_plates_absmean_gt_0p3_sigma":
            round(n_biased_samples / n, 4),
        "n_tail_abs_gt_1p5_sigma": tail_total,
        "frac_tail_on_biased_plates_gt0p3":
            round(frac_biased, 4),
        "per_plate": plate_rows,
    }


def bias_cells(samples: list[dict], top: int = 5) -> list[dict]:
    """Worst plate-dish cells: per-plate mean signed error with per-view
    detail, sorted by |mean err| DESC (top `top` plates)."""
    by: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by[s["plate"]].append(s)
    rows = []
    for plate in sorted(by):
        recs = by[plate]
        rows.append({"plate": plate, "n": len(recs),
                     "mean_err": round(float(np.mean([r["err"] for r in recs])), 2)})
    rows.sort(key=lambda r: (-abs(r["mean_err"]), r["plate"]))
    for r in rows[:top]:
        views = [{"dish": s["dish"], "pred": round(s["pred"], 1),
                  "gt": s["gt"], "err": round(s["err"], 1)}
                 for s in samples if s["plate"] == r["plate"]]
        r["views"] = views
    return rows[:top]


def compile_report(samples: list[dict]) -> dict:
    """Deterministic report body — the part the hermetic tests cover."""
    rows = plate_table(samples)
    total = float(sum(r["abs_err"] for r in rows))
    top_k = [concentration(rows, k) for k in (1, 2, 3, 4, 5)]
    jk = jackknife(samples)
    return {
        "n_samples": len(samples),
        "n_plates": len(rows),
        "mae_g": round(overall_mae(samples), 4),
        "total_abs_err_g": round(total, 4),
        "sum_signed_err_g": round(float(sum(s["err"] for s in samples)), 4),
        "mean_signed_err_g": round(float(np.mean([s["err"] for s in samples])), 4),
        "plates_top_k": top_k,
        "gini": gini(rows),
        "jackknife": jk,
        "jackknife_min_delta": jk[0],
        "jackknife_max_delta": jk[-1],
        "plate_rows": rows,
        "dish_rows": dish_table(samples),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default="dev", choices=("dev",),
                    help="DEV only — the only tuning tier")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="smoke only")
    ap.add_argument("--report-out", default=str(REPORT_PATH))
    args = ap.parse_args(argv)
    t0 = time.time()

    import torch
    import yaml

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

    rep = compile_report(samples)
    sigma_doc = yaml.safe_load(
        (_ROOT / "data" / "weight_head_sigma.yaml").read_text())
    sig_g = {k: float(v) for k, v in sigma_doc["sigma_g"].items()}
    sig_rel = {k: float(v) for k, v in sigma_doc["sigma_rel"].items()}
    if args.limit is None:
        prof = oof_coverage_profile(samples, sig_g, sig_rel)
        suspects = bias_cells(samples)
    else:
        prof = {"skipped": "smoke limit"}
        suspects = []
    rep["oof_profile"] = prof
    rep["worse_plates_top5"] = suspects
    rep.update({
        "ticket": TICKET, "ledger_entry": LEDGER,
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "tier": args.tier, "limit": args.limit,
        "checkpoint": "data/weight_head.pt",
        "checkpoint_meta": getattr(model, "meta", {}),
        "expected_mae_g": EXPECTED_MAE_G,
        "expected_oof_t1_coverage": EXPECTED_OOF_T1,
        "sigma_file": {"sigma_g": sig_g, "sigma_rel": sig_rel},
        "device": str(device),
        "samples": [{k: s[k] for k in ("plate", "dish", "pred", "gt", "err")}
                    for s in samples],
    })

    print(f"tier={args.tier} plates={rep['n_plates']} "
          f"samples={rep['n_samples']} mae={rep['mae_g']} "
          f"(expected {EXPECTED_MAE_G})", flush=True)
    for c in rep["plates_top_k"]:
        print(f"tier={args.tier} top{c['k']}_of_{rep['n_plates']}: "
              f"share={c['share']} uniform={c['uniform_share']}", flush=True)
    print(f"tier={args.tier} gini={rep['gini']}", flush=True)
    print(f"tier={args.tier} jackknife extremes: "
          f"min {rep['jackknife_min_delta']} "
          f"max {rep['jackknife_max_delta']}", flush=True)
    if args.limit is None:
        print(f"tier={args.tier} oof_t1_band="
              f"{prof['pooled_oof_coverage_90_band_at_t_1_0']} "
              f"(expected {EXPECTED_OOF_T1}) plate_mean_ssr_std="
              f"{prof['plate_mean_std_resid_std']} iid_exp="
              f"{prof['iid_expected_std_of_plate_mean_std_resid']}",
              flush=True)
        print(f"tier={args.tier} worst plates: "
              f"{[(r['plate'], r['mean_err']) for r in suspects[:3]]}",
              flush=True)

    rep["wall_s"] = round(time.time() - t0, 2)
    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2) + "\n")
    print(f"tier={args.tier} wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
