# NutriSense — Data Collection Field Manual (Golden Set)

**Purpose:** step-by-step instructions for collecting the 30 golden plates at the
school, tuned to the 5 days before Review 2. Every number here is taken from the
pipeline's actual configuration (`data/anchor_config.json`, `data/standards.yaml`,
`engine/pipeline.py`, `data/menu.yaml`) — following it guarantees the pipeline can
measure the photo instead of returning `cannot_verify`.

**Companion docs:** quick version → [`protocol.md`](protocol.md); why each split
exists → [`final-report.md`](final-report.md).

---

## 1. What counts as a golden plate

A folder is a valid golden plate only if **all** of the following hold:

- [ ] Photo taken with **digital zoom OFF** (EXIF zoom = 1.0) — otherwise the
      pipeline hard-fails with `cannot_verify`
- [ ] **Reference card visible, flat, same surface as the vessel** (required in
      every photo), marker sharp
- [ ] **Whole vessel + food + card inside the frame**, nothing cropped
- [ ] Original file with **EXIF intact** (focal length readable — the pose
      calculation needs it)
- [ ] **Net weight measured** on a 1 g kitchen scale (tare first)
- [ ] `meta.json` + `weights.json` filled at capture time
- [ ] Dish is on **that day's menu** in `data/menu.yaml` (see §2)

Anything less → keep the photo as a *gallery/reference* shot, but do **not** put
it in `DATASET/golden/`.

---

## 2. The 5-day plan (menu + plate quotas)

The Karnataka MDM menu rotates like this (from `data/menu.yaml`):

| School day | Dish served | menu.yaml id | Capturable? |
|---|---|---|---|
| Mon | Rice & Sambar (pepper/tomato rasam rice variants) | `rice_sambar` (aliases `pepper_rasam_rice`, `tomato_rasam_rice`) | ✅ |
| Tue | Rice & Sambar | `rice_sambar` | ✅ |
| Wed | Rice & Sambar | `rice_sambar` | ✅ |
| Thu | Rice & Sambar | `rice_sambar` | ✅ |
| Fri | Bisi Bele Bath | `bisibelebath` | ✅ (needs ≥ 2 **dev** plates — M7 rule) |
| Sat | Wheat product (roti/chapati) | `wheat_product` | ❌ out of scope — never capture |
| any | Vegetable Rice | `vegetable_rice` | not on the current schedule (days: []) |

**Splits (30 plates total):** pilot 4 · dev 13 · holdout 13.

- **pilot (4)** — first day, tray totals only. Proves the card/depth pipeline
  works on real photos (M0b go/no-go). Stop and reassess if tiers fall back.
- **dev (13)** — per-dish weights. The ONLY plates used to tune σ, temperature
  and composition rules.
- **holdout (13)** — sealed. Never opened, never tuned against; evaluated once
  at M8 and labelled `indicative`.

**Recommended daily quota (~6 valid plates/day + 1 spare):**

| Day | Pilot | Dev | Holdout | Day total |
|---|---|---|---|---|
| Day 1 (Mon) | 4 | 2 | 0 | 6 |
| Day 2 (Tue) | 0 | 3 | 3 | 6 |
| Day 3 (Wed) | 0 | 3 | 3 | 6 |
| Day 4 (Thu) | 0 | 3 | 3 | 6 |
| Day 5 (Fri) | 0 | 2 | 4 | 6 |
| **Total** | **4** | **13** | **13** | **30** |

- Day 5 gives the 2 required Bisi Bele Bath **dev** plates (`min_dev_plates: 2`).
- If a capture fails QA, shoot a spare the same day; only QA-passed plates count.
- If the school serves a dish **not** on that day's menu row, skip it (the API
  rejects it) and note the substitution in the debrief (§13).

**Bands:** record the real class band of the children the tray was served to —
`1-5`, `6-8`, or `9-10`. If the school serves both a primary and a higher band,
capture a mix (their minimums differ: 450 kcal/12 g vs 700 kcal/20 g).

---

## 3. Gear checklist (pack the night before)

- [ ] Reference card × 2 (laminated if possible) — `docs/assets/reference_card_A6_300dpi.png`
- [ ] Steel ruler (mm scale) — to verify the printed card once (Day-0)
- [ ] Kitchen scale, **1 g resolution**, working batteries
- [ ] Phone + **charging cable / power bank** (transfer + long day)
- [ ] Printed checklist (§11) + pen, or notes app open to §10 templates
- [ ] Tissue/lens cloth (steam and fingerprints ruin markers)

---

## 4. Day-0 setup (do once, before Day 1)

1. **Print the card:** A6 paper (105 × 148 mm), 300 dpi asset, **100% scale —
   printer "fit to page" OFF**, borderless if supported.
2. **Ruler-check the black square:** it must measure **exactly 100.0 mm ± 0.5 mm**
   edge to edge. If off → reprint, or measure the actual size, write it into
   `data/anchor_config.json` → `card.square_mm`, then set
   `"ruler_checked": true` with the date in `ruler_checked_note`.
   *This square is the metric ground truth for every measured plate — 1 mm of
   error here becomes 1% scale error in every verdict.*
3. **Check the ArUco marker:** 60.0 mm square (DICT_4X4_50, id 7), white quiet
   zone around it must stay clean — do not tape over it, do not fold.
4. **Test the scale:** weigh a known mass (e.g. an unopened 500 ml water bottle
   = 500 g). It must read within ±5 g. Zero/tare before every use.
5. **Phone camera defaults** (see §5) set and locked in the camera app.
6. **Confirm with the kitchen:** serving time, which band eats where, what
   vessel/tray types are used (plate vs bowl vs compartment tray), and that you
   may photograph and weigh one portion.

---

## 5. Camera settings (set once, keep fixed)

| Setting | Value | Why |
|---|---|---|
| Lens | **1× main camera** | zoom is a hard gate |
| Digital zoom | **OFF (must read 1.0)** | `zoom != 1.0` → `cannot_verify` |
| Resolution | **highest available, ≥ 1280 px min side** (ideally 4000 × 3000) | below 1280 the API adds a resolution note and the marker tier may fall back |
| Aspect ratio | **4:3** (full sensor) | maximum detail, no crop |
| Flash | **OFF** | reflections wash out the ArUco marker |
| HDR / AI scene / beauty / filters | **OFF** (or "off" in Pro mode) | keeps the marker contrast honest, no re-sharpening artifacts |
| Grid lines | **ON** | helps hold the 30–45° tilt (§6) |
| Timer / steady grip | 2 s timer or steady hands | motion blur = lost marker |
| File format | JPEG, **original (unprocessed)** file | pipeline reads JPEG + EXIF |
| EXIF / location tags | **KEEP** | focal length feeds the pose solver; stripping it degrades tilt accuracy |

Never edit, crop, rotate or re-export the photo before analysis.

---

## 6. Geometry — height, distance, angle

Hold the camera **above the near edge of the tray, leaning over the table**:

| Parameter | Target | Hard limit |
|---|---|---|
| Tilt from vertical | **30–45°** | **< 50°** |
| Distance camera → card plane (along the lens axis) | **30–40 cm** | marker ≥ 80 px |
| Camera height above the table | **25–35 cm** | — |
| Horizontal standoff from vessel centre | **15–25 cm** | — |
| Frame width at the table | **45–55 cm** | tray + card + margin must fit |

**On-screen verification (this is the real test — check before pressing the
shutter):**

1. The **ArUco marker spans roughly ⅛ of the frame width**
   (≈ 160 px on a 1280 px image, ≈ 500 px on a 4000 px image).
   Absolute floor in config: **80 px** — never ship a photo below it.
2. The **whole vessel, all the food, and the full card** are inside the frame
   with a small margin of table visible on all sides.
3. Food is **in focus** (tap the screen on the food, then lock AE/AF if the
   phone has it).

> Quick intuition: at 30–40 cm with the main lens, the frame is about a
> forearm's width across the plate. If you have to pinch-zoom to fit the tray,
> you are too far — move closer instead of zooming.

The pipeline reports what it achieved: after upload, check the result's
`anchor.tier` (must be `measured`) and `anchor.tilt_deg` (will be ~30–45).

---

## 7. Card placement

- **The card is required in every photo** — without a usable card the pipeline
  falls back to size priors (coverage capped 0.60, never PASS/FAIL) and the
  plate must be re-shot for the golden set.
- Card lies **flat on the table, beside the vessel, on the same surface plane**.
- Card **fully visible**, not overlapping or under the vessel, not held in a
  hand, not leaning against anything.
- Marker faces the camera as squarely as the tilt allows; avoid folding/creases.
- **No reflections** across the marker (angled overhead lights — shift the card
  a few degrees or your own position).

---

## 8. Lighting & food condition

- Even overhead light or shade; **no harsh direct sun spots** on the plate/card.
- **No backlight** (window behind the food) — meter on the food.
- Shoot the food **as served** — do not restyle, stir or garnish it.
- Wipe steam off the lens; heavy steam fog = reshoot.
- Plain, matte table surface if you can choose (shiny steel reflects).

---

## 9. Per-plate procedure (repeat for every plate)

1. **Place** the vessel centred; wipe drips off the table.
2. **Place the card** flat beside it (§7).
3. **Tare the scale** with the *empty* vessel on it → record `vessel_g`.
   *(For pilot plates you weigh after shooting — order below handles both.)*
4. **Frame** the shot (§6): tilt 30–45°, marker ≈ ⅛ width, everything inside.
5. **Shoot.** Immediately review at 100% zoom: marker sharp? tray fully in
   frame? no reflections? → reshoot now, not later.
6. **Weigh** while the food is fresh:
   - empty vessel on scale → tare → `vessel_g`
   - food + vessel → `total_net_g` (total) — net food = total − tare
   - **dev & holdout only:** weigh each component separately before mixing
     (rice portion, sambar portion, …) → `per_dish` array
7. **Fill the metadata immediately** (§10) — memory is not a data source.
8. **Move the files** to the day's transfer folder (§11) before leaving the
   serving area.
9. **Run the QA checklist** (§12) on every photo before you leave the school.

**Time budget:** arrive ~15 min before serving; each plate ≈ 3–4 min
(2 photos + weigh + metadata).

---

## 10. Metadata templates

### `meta.json` (one per plate)

```json
{
  "plate_id": "dev/plate_03",
  "day": "tue",
  "band": "1-5",
  "dish": "rice_sambar",
  "serving_style": "mixed",
  "camera": "your phone model",
  "captured_at": "2026-10-13T12:45:00",
  "anchor": {"card_present": true, "ruler_checked": true},
  "notes": ""
}
```

| Field | Values | Rule |
|---|---|---|
| `day` | `mon, tue, wed, thu, fri, sat` | must match the school day |
| `band` | `1-5`, `6-8`, `9-10` | the band the tray was served to |
| `dish` | menu.yaml id or its alias (`pepper_rasam_rice` → `rice_sambar`) | must be served **that day** or the API rejects it |
| `serving_style` | `mixed` = components stirred together; `single` = served separate | affects composition rules |
| `anchor` | which markers were actually in the photo | drives tier expectations |
| `notes` | free text | substitutions, odd lighting, etc. |

### `weights.json` (one per plate)

```json
{
  "vessel_g": 320,
  "total_net_g": 465,
  "per_dish": [{"name": "rice_sambar", "g": 465}],
  "scale": "kitchen_scale_1g"
}
```

- **pilot:** tray totals are enough (`per_dish` may equal the total).
- **dev/holdout:** `per_dish` must list the real component weights.
- Expected sane range (flag-only, never auto-rejects): band `1-5` →
  **300–500 g**, bands `6-8`/`9-10` → **450–750 g** (`plate_sanity_g`).

---

## 11. File handling & transfer

```
DATASET/golden/
  pilot/plate_01/{photo.jpg, meta.json, weights.json}
  pilot/plate_02/...
  dev/plate_01/...
  holdout/plate_01/...
```

- File name: **`photo.jpg`**, lowercase `.jpg` (the gallery tool only globs
  `*.jpg`).
- **Transfer with a USB cable / Files app / local network copy — originals
  only.** NEVER WhatsApp, Telegram, Instagram, Messenger or any chat app:
  they re-compress the image **and strip EXIF**, which breaks the zoom gate and
  the pose solver.
- Do not rename inside the file, do not crop, do not "send as document" from a
  chat app.
- Keep the phone originals until the project is submitted (backup on a laptop
  each evening).
- **Golden plates never go into `DATASET/<dish>/*.jpg`** (that location feeds
  the classifier gallery and would leak the evaluation set). Only non-golden
  dish photos belong there.

---

## 12. On-site QA checklist (run on every photo)

- [ ] Zoom was 1× (never pinch-zoomed)
- [ ] At 100% review: marker sharp, ≥ ⅛ of frame width
- [ ] Whole vessel + all food + full card in frame
- [ ] No reflection band across the marker
- [ ] Tilt looks like 30–45° (not flat overhead, not near-horizontal)
- [ ] Photo info still shows focal length (EXIF present)
- [ ] `meta.json` + `weights.json` filled and match the photo
- [ ] `day`, `dish`, `band` match the actual menu/serving
- [ ] Net weight inside the sanity band (or explained in `notes`)
- [ ] Files already moved off the phone into the day's folder

---

## 13. Common failures → cause → fix

| Symptom (in API result) | Cause | Fix |
|---|---|---|
| `cannot_verify — digital zoom != 1.0` | pinch-zoom used | reshoot at 1× |
| `tier: prior`, coverage capped 0.60 | card not found: cropped, covered, tilted, blurry, or < 80 px | card flat, fully visible, move closer |
| resolution note (< 1280 px) | low-res mode or crop | set highest resolution, 4:3 |
| `unrecognized dish` | dish not in gallery/aliases, or photo too dark | check menu id/alias; reshoot brighter |
| grams ≈ 0 / tiny mask | segmentation failed (known weakness on real photos — why pilot exists) | reshoot sharper, plainer background, more top-down within 45° |
| verdict `cannot_verify`, day/band error | metadata mismatch vs `data/menu.yaml` | fix meta.json (don't force wrong day) |
| weight outside sanity band | scale not tared / wrong vessel / wrong band recorded | reweigh, recheck tare and band |

---

## 14. After collection — verify, tune, test

### 14.1 Verify every plate (end of each day)

1. Start the stack: `.venv/bin/uvicorn main:app --port 8731` + `npm run dev`.
2. Analyze each plate in the app (**Analyze Meal**) with its true day/band.
3. For each plate record: `anchor.tier` (expect **measured**), `tilt_deg`
   (30–45), reported grams vs scale, verdict.
4. **M0b gate (end of Day 1):** if the 4 pilot plates mostly land on
   `measured` and grams are in a sane range → continue the plan. If most fall
   back to `prior`, stop and fix capture technique before burning dev/holdout
   plates (this is exactly what pilot is for).

### 14.2 Gallery (classifier) — optional, leak-safe

- New *reference* photos of dishes (no golden evaluation plates) go in
  `DATASET/<class_dir>/*.jpg` (one level deep), then rebuild:
  `.venv/bin/python -m tools.build_gallery --source ../DATASET --out data/gallery.npz`
- Current gallery: 46 photos, leave-one-out 46/46, abstain threshold 0.82.
- **Never** copy golden plates into those class folders (folder layout in §11
  keeps them out automatically — do not flatten).

### 14.3 Tuning (dev plates only)

- Dev plates are the only input for calibrating:
  - **M1** — reported grams vs kitchen-scale weight (per-plate % error table).
  - composition/shares, `temperature_scale`, σ values in
    `data/params_status.yaml` — update the `value` and change `status` from
    `assumed` toward measured when evidence supports it.
- **Do not touch** holdout plates, and do not tune to make a specific plate pass.

### 14.4 Holdout discipline

- `holdout/` is opened **once**, after tuning is frozen (M8).
- Results are labelled `indicative` in the report; per-plate errors stay sealed
  until then.

### 14.5 What to report at Review 2

- Per-plate table: id · day · band · tier · tilt · scale g · reported g ·
  error % · verdict.
- Pilot gate outcome, any protocol deviations, dev-tuning changes made, and
  the number of valid plates per split.

---

## 15. Privacy

- Photograph **trays and food only** — no children, faces, uniforms, name tags
  or class boards in the frame.
- Student names belong only in the local app (Student Records), never in
  golden metadata or filenames.
- Follow any consent/permission the school requires before photographing.

---

## 16. Daily debrief log (fill each evening)

| plate | tier | tilt° | scale g | reported g | error % | sanity flag | notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

End-of-day routine: verify all plates (§14.1) → back up originals → fill this
log → update the quota table (§2) with what's left to collect.
