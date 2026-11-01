# Meal critique demo setup

NutriSense requests a short critique after each new analysis. The result page
stores that critique with the analysis; the user can open a meal-scoped chat
and successful turns are saved in the same browser record. Existing analyses
from before this feature are not automatically sent to a model.

## Configure Ollama Cloud

The backend reads these environment variables:

| Variable | Purpose |
| --- | --- |
| `OLLAMA_API_KEY` | Secret API key for the backend only. Never put it in frontend code or a `VITE_*` variable. |
| `NUTRISENSE_CHAT_MODELS` | One to three comma-separated model IDs, tried in order. Set only IDs currently included in your account's free allowance. |
| `OLLAMA_CLOUD_URL` | Optional API base URL; defaults to `https://ollama.com`. |

Ollama changes which models are included in free starter usage. Confirm the
models in your account before configuring a demo. Gemma 4 Cloud is currently
listed with per-token pricing, so do not include it if you require a strictly
free demo. Free allowance limits reset monthly; when every configured model is
unavailable or out of allowance, the API reports the critique/chat as
unavailable and does not switch to an unconfigured paid model. The chain only
tries the IDs you set, so it cannot verify their billing status on your
behalf.

Example shell configuration (replace the model names with IDs shown as free
in your account):

```sh
export OLLAMA_API_KEY='your-key'
export NUTRISENSE_CHAT_MODELS='free-model-one,free-model-two,free-model-three'
```

Restart the FastAPI process after changing these values. If no key or model
IDs are configured, meal analysis still works and the result page shows that
the critique service is unavailable.

## Data sent to Ollama

The backend sends detected food labels, estimated grams, available energy and
protein estimates, component provenance, assumptions, and the current verdict.
It does not send the meal photo, student name, or local chat history beyond the
last four turns. Model output is advisory, is limited to the analyzed meal,
and should not be treated as medical advice. Nutrition values may be assumed
or incomplete, and the system has not been validated as a production nutrition
advisor.

Critique and chat endpoints use a 35-second timeout per model and try up to
three configured models in order. A user can retry an unavailable automatic
critique. Follow-up messages are saved only after a successful model reply.
