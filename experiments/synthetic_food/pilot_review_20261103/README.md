# Synthetic pilot human review package

This directory is a separate visual review package for the existing renderer
pilot. The source pilot manifest and validation artifacts were not modified.

## Open the gallery

Open `index.html` in a browser. It has all 41 isolated
classes and 3 composed thali pairs. For every
pair it places card-present and card-absent scenes side by side, each with the
original RGB, food-class mask, component mask, object mask, metric-depth view,
and world-space geometry projection.

The depth color scale is fixed at 0.15–1.20 m. The 3D geometry panel is a
deterministic orthographic projection of renderer-provided world XYZ; it is a
diagnostic view, not a new geometry estimate.

## Fill the review sheet

Edit `review_sheet.csv`. Valid status values are `PASS`, `FAIL`, and
`REVIEW_REQUIRED`. The `automated_pair_check_status` column records software
checks only. Leave any human decision `REVIEW_REQUIRED` until a person has
visually inspected it. `marker_detection_pose_card_absent` is
`NOT_APPLICABLE` because the no-card view intentionally has no marker.

Evaluate identity/appearance, shape and portion plausibility, texture/color,
artifacts, mask alignment, metric depth, 3D geometry/volume, mass-density
provenance, marker pose, thali believability, and whether foods are visually
distinguishable. Realistic-looking RGB does not by itself validate physical
labels. Record failed dimensions and reasons separately, and set a retention
decision only after review.

## Automated matched-pair audit

`pair_verification.json` independently compares scene configuration,
camera, illumination, background/noise, masks, component mass/volume/density,
depth and world geometry outside the projected card area, RGB difference
extent, and marker presence. Results: 44/
44 automated pairs pass. Human pair consistency still
requires review.

Source pilot manifest SHA-256: `cda0d8c4ecde7ab9a4bbc43cb9cd34a033e4ad88d8f3135b4b972c226f943314`  
Source pilot validation SHA-256: `f5a30f497bcd0d1e68eca84c3839ad69bdc5b0ce231476d2f3eb40ea671724a7`

The package adds diagnostic visualizations only; it generates no new food
scenes, does not train models, and uses no DEV, LOCKED, ArUco evaluation, or WED
test data.
