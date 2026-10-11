# Pipeline performance baseline

Wall time and peak VRAM for one full `engine.pipeline.analyze()` call,
measured by `tools/profile_pipeline.py` (script-local wrapper around
`engine.pipeline.stage`; the pipeline itself is untouched).

Method: 4 runs per input; run 1 is warm-up (model loads, cudnn autotune)
and dropped; median and p95 over the remaining 3 runs. Peak VRAM is
`torch.cuda.max_memory_allocated()` per run, reset before each run.
Inputs:

* **synthetic** — no-card scene from `tests.synth.scene`, classifier stubbed
  to `rice_sambar` (the real gallery abstains on renders, which would skip
  depth/portion/nutrition and leave the baseline incomplete);
* **real** — `DATASET/pepper_rasam_rice/IMG20260824131408.jpg` (read-only),
  real classifier (verdict FAIL, full pipeline runs).

Machine: Linux 7.2.9-2-cachyos, Python 3.14.7, torch 2.13.0+cu130,
NVIDIA GeForce RTX 4060 Laptop GPU (8 GB).
`after` column = same script re-run after the STAGE 2 model registry
refactor; the synthetic pipeline output JSON is compared field-by-field
against `/tmp/golden_before.json` (floats within 1e-6).

| stage (synthetic) | before median ms | before p95 ms | after median ms | after p95 ms |
|---|---|---|---|---|
| segment | 380.5 | 382.9 | | |
| classify (stub) | 0.0 | 0.0 | | |
| depth | 264.0 | 265.7 | | |
| portion | 15.0 | 20.3 | | |
| nutrition (MC 4000) | 1.1 | 1.2 | | |
| **total** | **662.7** | **672.1** | | |
| peak VRAM MiB | 3285.3 | 3285.3 | | |

| stage (real photo) | before median ms | before p95 ms | after median ms | after p95 ms |
|---|---|---|---|---|
| segment | 393.5 | 399.1 | | |
| classify (SigLIP2) | 29.1 | 36.8 | | |
| depth | 410.2 | 411.0 | | |
| portion | 80.0 | 81.1 | | |
| nutrition (MC 4000) | 1.2 | 1.5 | | |
| **total** | **941.6** | **945.3** | | |
| peak VRAM MiB | 4841.3 | 4841.3 | | |

Notes:

* Warm-up runs (first touch of each model) cost ~11–12 s on this box and
  are excluded by design.
* Classification on the synthetic input is a stub by construction; the real
  photo carries the true SigLIP2 number.
* Baseline captured at git `0993e5c` (pre-registry).
