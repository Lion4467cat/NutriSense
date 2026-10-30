# MetaFood3D local dataset inventory

## Local source files

The dataset is organized under `datasets/raw/marker/metafood3d/`:

```text
datasets/raw/marker/metafood3d/
├── archives/       Original compressed downloads, preserved
├── metadata/       Source README and nutrition/weight workbook
└── extracted/      Extracted dataset files, in source folder structure
    ├── 3D_Mesh/
    ├── Point_cloud/
    ├── RGBD_videos/
    └── RGBD_videos_flipped_food/
```

Original archive files are retained unchanged:

- `archives/_MetaFood3D_new_3D_Mesh.tar.gz`
- `archives/_MetaFood3D_new_Point_cloud.tar.gz`
- `archives/_MetaFood3D_new_RGBD_videos.tar.gz`
- `archives/_MetaFood3D_new_RGBD_videos_flipped_food.tar.gz`
- `metadata/_MetaFood3D_new_complete_dataset_nutrition_v2.xlsx`
- `metadata/_MetaFood3D_Readme.txt`

The separate 137 GB package mentioned by the user is not present; its exact
contents are not established. The source README mentions Blender-rendered
images and camera parameters, but no separate Blender-render archive was
found. The four archives listed above have been extracted. Extraction is not
an evaluation or validation of the dataset.

## Dataset notes

The supplied README describes textured 3D meshes, RGBD video frames with
segmentation masks and depth maps, flipped-food video for a subset, 1024-point
clouds, and a nutrition workbook. The workbook contains 637 rows for 108
`Object_name` values and includes `Weight (g)`; 636 rows have a weight and one
row does not. An inventory of the extracted standard RGBD tree found 637
object directories, with 101,658 `original`, depth, and mask frames, 101,579
segmented frames, and 101,579 frame stems present in all four modalities.
Six object directories have unequal modality frame counts; in each, some
segmented frames are absent. Do not silently treat those frames as aligned.

The workbook and RGBD paths join on 631 of 637 object names after case-folding
the category and instance names. Six paths do not match the workbook exactly:
`Carrot/carrot_8` vs `Carrot/carrrot_8`,
`Edamame/new_edamame_4` vs `Edamame/new_edammame_4`,
`Peanuts/new_peanut_{1,2,4}` vs `Peanuts/peanuts_{1,2,4}`, and
`Stew_Beef/new_beef_stew_3` vs `Stew_Beef/beef_stew_3`. These are recorded as
unmatched rather than silently corrected. Recompute the inventory before
defining any experiment subset. The
[official dataset page](https://lorenz.ecn.purdue.edu/~food3d/) reports 637
food objects in 108 categories and says fiducial-marker images are included
in video capture. The local archive's marker type and marker-to-frame/weight
association have not yet been verified.

## Initial file-level audit

In one sampled `Almond(bowl)/almond_1` sequence, the `original`, `segmented`,
`masks`, and `depth` directories each contained 200 frames with matching
names and 1440×1920 dimensions. The sampled mask includes the bowl and food as
one region, so it is not a food-only item annotation. The original image
shows a color checker and a fiducial-looking board outside that mask; marker
family and IDs have not been decoded. The sampled depth JPEG is three-channel
colorized imagery, and no local depth encoding, units, or camera calibration
were established. Treat it as non-metric until a source specification or
known-distance validation confirms otherwise. These are findings from one
sampled sequence, not a full visual audit.

Treat physical object identity as the grouping key; keep views of one object
together in any split. Do not assume that a random image split is independent.

This is a research dataset licensed CC BY-NC 4.0 per the project dataset
registry. Keep the source local; do not commit archives, extracted images,
weights, or model artifacts. The dataset is a separate single-object task and
must not be concatenated with WED plate labels. Its suitability for measuring
improvement to the current plated-meal pipeline remains unverified.

## Current use boundary

A first research-only image-plus-mask mass benchmark was run on 630 exact-join
weighted objects with a group-disjoint 416/106/108 train/dev/test split. The
candidate failed its prewritten test criterion against the train-only
category-median baseline; details and the reproducible command are in
`experiments/metafood3d/RESULTS.md`. No serving code changed. Do not retune on
that test split. The file-level audit remains incomplete: the workbook
`Volume` unit/derivation, marker family/IDs, and metric depth encoding are
unverified. Any further evaluation must remain group-disjoint by physical
object and separate from WED. Raw data and experiment outputs under
`datasets/raw/` are ignored by Git and must not be committed. The official
dataset terms restrict use to non-commercial purposes.
