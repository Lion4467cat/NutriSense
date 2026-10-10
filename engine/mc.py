"""S4: Monte-Carlo nutrient engine — the SOLE interval owner.

Takes the S3 point estimate (grams + named relative sigmas) and samples:
  grams        — lognormal matched to portion["sigma_grams_rel"]
                 (already quadrature of depth / area / base / density)
  shares       — recipe composition noise, renormalised (multi-component)
  kcal/protein — per-100 g table values widened by nutrient_table_sigma_pct
                 (+ component_value_sigma_pct for generic/wider recipes)

Raw-ingredient equivalents (rice_yield style conversions) are DIAGNOSTIC
only — never verdict input (standards.yaml: raw_gram_rows: informational).

Interval width is tuned by params temperature_scale (M6 calibration hook).
"""
import numpy as np

from config import load_params, load_standards, load_yields
from engine.nutrients import assumed_nutrient_ids, nutrient_value, load_nutrients


def _lognormal_mean1(rng, sigma_rel, n):
    """Samples with mean 1 and relative std sigma_rel."""
    if sigma_rel <= 0:
        return np.ones(n)
    s2 = np.log1p(sigma_rel * sigma_rel)
    return rng.lognormal(mean=-0.5 * s2, sigma=np.sqrt(s2), size=n)


def _normal_pos(rng, mean, sigma_rel, n):
    if sigma_rel <= 0:
        return np.full(n, float(mean))
    return np.maximum(rng.normal(mean, sigma_rel * mean, n), 1e-6)


def _summary(samples, temperature=1.0):
    """Central interval widened by the temperature parameter (M6 hook)."""
    mean = float(np.mean(samples))
    p05, p50, p95 = (float(x) for x in np.percentile(samples, [5, 50, 95]))
    lo = p50 - temperature * (p50 - p05)
    hi = p50 + temperature * (p95 - p50)
    return {
        "mean": mean,
        "sd": float(np.std(samples)),
        "p05": lo,
        "p50": p50,
        "p95": hi,
        "interval_90": (lo, hi),
    }


def sample_nutrients(portion, dish, band=None, n=4000, seed=1234,
                     nutrients=None, params=None, standards=None, yields=None):
    """Run the MC. Returns samples (for verdict math) + summaries + diagnostics."""
    params = params if params is not None else load_params()
    nutrients = nutrients if nutrients is not None else load_nutrients()
    standards = standards if standards is not None else load_standards()
    yields = yields if yields is not None else load_yields()
    rng = np.random.default_rng(seed)

    comps = dish["components"]
    names = list(comps.keys())
    shares0 = np.array([float(comps[nm].get("share", 1.0)) for nm in names])
    shares0 = shares0 / shares0.sum()

    # grams
    g_sigma = float(portion["sigma_grams_rel"])
    grams_s = float(portion["grams"]) * _lognormal_mean1(rng, g_sigma, n)

    # recipe shares (skip noise for single-component dishes)
    if len(names) > 1:
        s_rel = params["recipe_composition_sigma_pct"]["value"] / 100.0
        noisy = shares0[None, :] * _lognormal_mean1(rng, s_rel, n)[:, None]
        shares_s = noisy / noisy.sum(axis=1, keepdims=True)
    else:
        shares_s = np.repeat(shares0[None, :], n, axis=0)

    # per-100g nutrient values
    generic_wider = bool(dish.get("ranges_wider"))
    table_rel = params["nutrient_table_sigma_pct"]["value"] / 100.0
    value_rel = np.hypot(
        table_rel,
        (params["component_value_sigma_pct"]["value"] / 100.0) if generic_wider else 0.0,
    )
    kcal_pp100, prot_pp100 = [], []
    for nm in names:
        k, p, _ = nutrient_value(comps[nm]["generic_id"], nutrients)
        kcal_pp100.append(_normal_pos(rng, k, value_rel, n))
        prot_pp100.append(_normal_pos(rng, p, value_rel, n))
    kcal_pp100 = np.stack(kcal_pp100, axis=1)   # (n, c)
    prot_pp100 = np.stack(prot_pp100, axis=1)

    grams_c = shares_s * grams_s[:, None]        # (n, c)
    kcal_s = (grams_c / 100.0 * kcal_pp100).sum(axis=1)
    prot_s = (grams_c / 100.0 * prot_pp100).sum(axis=1)

    temperature = float(params.get("temperature_scale", {}).get("value", 1.0))

    # raw-equivalent diagnostic (type -> yield key)
    type_yield = {"grain": "rice", "dal": "pulses", "vegetable": "vegetables",
                  "grain_pulse_mix": "mixed"}
    raw_point = {}
    for i, nm in enumerate(names):
        t = comps[nm].get("type", "grain")
        yk = type_yield.get(t, "rice")
        if yk == "mixed":
            y = 2.0 / (1.0 / yields["rice"]["yield"] + 1.0 / yields["pulses"]["yield"])
        else:
            y = float(yields[yk]["yield"])
        raw_point[nm] = float(portion["components_g"][nm]) / y

    alloc = None
    if band and band in standards["allocation_raw_per_day"]:
        alloc = dict(standards["allocation_raw_per_day"][band])

    return {
        "seed": int(seed),
        "n": int(n),
        "kcal_samples": kcal_s,
        "protein_g_samples": prot_s,
        "grams_samples": grams_s,
        "kcal": _summary(kcal_s, temperature),
        "protein_g": _summary(prot_s, temperature),
        "grams": _summary(grams_s, temperature),
        "components_g": {
            nm: _summary(grams_c[:, i], temperature) for i, nm in enumerate(names)
        },
        "diagnostics": {
            "raw_equivalent_g": raw_point,
            "raw_allocation_per_day_g": alloc,
            "raw_basis_note": "raw allocations are per-child/day; plate raw-equivalent "
                              "is informational only (never verdict input)",
        },
        "assumed_nutrients": assumed_nutrient_ids(dish, nutrients),
        "wider_ranges": generic_wider,
    }
