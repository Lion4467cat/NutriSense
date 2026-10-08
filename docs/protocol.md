# NutriSense capture protocol (golden set)

Goal: 30 golden plates — 4 pilot / 13 dev / 13 holdout — for calibration,
tuning, and a single sealed final evaluation.

## Day-1 (before any capture)

1. Print `docs/assets/reference_card_A6_300dpi.png` on **A6, 100% scale,
   no page-fitting** (borderless if possible).
2. Ruler-check the black square: **must be exactly 100.0 mm** (±0.5 mm).
   If off, reprint or measure the actual square and record it in
   `data/anchor_config.json` → `card.square_mm`, then set
   `ruler_checked: true` with date in `ruler_checked_note`.
3. Kitchen scale: 1 g resolution, zeroed with the empty vessel (tare).

## Per-capture rules

- Plain, matte table; even lighting; no HDR/digital zoom (zoom = 1.0).
- Vessel centred, **whole tray in frame**, slight top-down angle (tilt < 50°).
- **Card beside the vessel, same plane, fully visible, marker ≥ 80 px**
  (scale comes only from card/coin — never from vessel diameter).
  Coin (₹10 bimetallic) accepted if card missing; both present is fine
  (card wins).
- Focus on the food; no motion blur; keep original EXIF.
- Enter metadata in the plate's `meta.json` at capture time (below).

## Splits & what to weigh

| Split | n | Weighing | Purpose |
|---|---|---|---|
| pilot  | 4  | tray totals (per plate) | M0b go/no-go: does depth/scale pipeline behave |
| dev    | 13 | **per dish** in the tray | tune σ, temperature, composition rules |
| holdout| 13 | **per dish** | M8, opened once; results labeled `indicative` |

- Same scale and vessels across splits where possible.
- Record `vessel_g` (tare) and net food weight; 1 g resolution.
- Holdout stays out of any tuning; no peeking at per-plate errors before M8.

## Folder layout

```
DATASET/golden/
  pilot/plate_01/{photo.jpg, meta.json, weights.json}
  dev/plate_01/...
  holdout/plate_01/...
```

`meta.json`:
```json
{
  "plate_id": "dev/plate_03",
  "day": "mon", "band": "1-5", "dish": "rice_sambar",
  "serving_style": "mixed",
  "camera": "realme 14T", "captured_at": "2026-10-09T12:40:00",
  "anchor": {"card_present": true, "coin_present": false, "ruler_checked": true},
  "notes": ""
}
```
`weights.json`:
```json
{
  "vessel_g": 320, "total_net_g": 465,
  "per_dish": [{"name": "rice_sambar", "g": 465}],
  "scale": "kitchen_scale_1g"
}
```

## Capture lint (enforced by the pipeline)

- digital zoom == 1.0 (else `cannot_verify`)
- min side ≥ 1280 px, card marker ≥ 80 px (else `prior`)
- plate weight inside `plate_sanity_g` band in `data/standards.yaml`
  (loose ±25%; flag only, never auto-reject)
- day ∈ menu days, dish ∈ `data/menu.yaml` ids
