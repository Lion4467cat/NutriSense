# Reusable asset feasibility experiment

See [`REPORT.md`](REPORT.md) for the tool comparison, license assessment and
five-class results.

The reproducible CPU preview script imports five local MetaFood3D OBJ/MTL
assets into Blender and writes appearance-only renders under the ignored
`datasets/processed/reusable_assets_feasibility_20261103/` directory. The
comparison sheet pairs these with the existing class-surface pilot and its
eligible WED TRAIN references. No new WED image reads are performed here.

The MetaFood3D source is CC BY-NC 4.0. Keep the source assets and derived
preview images local to noncommercial research unless rights are separately
cleared. None of the proxy renders is approved as a WED-labeled training item.

Run:

```bash
blender -b -t 4 --python experiments/synthetic_food/reusable_assets_feasibility_20261103/render_metafood_assets.py -- \
  --mesh-root datasets/raw/marker/metafood3d/extracted/3D_Mesh \
  --output datasets/processed/reusable_assets_feasibility_20261103/metafood3d
python experiments/synthetic_food/reusable_assets_feasibility_20261103/build_comparison.py
```
