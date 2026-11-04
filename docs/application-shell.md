# Application shell and inference boundary

The browser talks to an `ApiClient`; it does not import inference modules.
The live client sends `POST /analyze` as multipart form data (`file`, `day`,
`band`, and optional `mode` / `serving_style`) and validates the complete
response against the generated Zod `analysisSchema`. Python's
`engine.contract.Analysis.to_wire()` remains the wire source of truth;
`tools/gen_contract_ts.py` generates the matching frontend schema.

The API decodes and bounds the uploaded image, builds an `AnalysisRequest`,
then hands pixels and metadata to `AnalysisService`. The service owns the
single-inference guard and accepts an `AnalysisPipeline` callable, so the
production pipeline, a mocked pipeline, or a later model adapter can be
supplied without changing the upload route.
The existing `engine.pipeline.analyze(..., deps=...)` remains the finer stage
seam for segmentation, classification, depth and weight implementations.

## Run the frontend demo without an API or ML models

From `frontend/`:

```sh
VITE_NUTRISENSE_DEMO=1 npm run dev
```

The local demo client returns a fixed, schema-validated multi-item response
for any selected image. It never sends the image over the network. The result
page and app banner identify the values as fixed sample data; they are not
predictions from the uploaded pixels. Menu, goals, critique and chat are also
local demonstration responses. Unset the variable to use the live API client.

## Checks

```sh
cd frontend
npx vitest run src/services/demoClient.test.ts src/pages/Analyze.demo.test.tsx
npx tsc --noEmit
```

The Python application-boundary test is CPU-only and injects a fake pipeline:

```sh
CUDA_VISIBLE_DEVICES='' ../.venv/bin/python -m pytest -q ../tests/test_application_service.py
```
