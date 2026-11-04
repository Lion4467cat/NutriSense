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
| `NUTRISENSE_CHAT_MODELS` | Optional override: one to three comma-separated model IDs, tried in order. The default is `beam:cloud`. |
| `OLLAMA_CLOUD_URL` | Optional API base URL; defaults to `https://ollama.com`. |

The Ollama model catalog currently marks Beam Cloud as free, so `beam:cloud`
is the default. Confirm its status in your account before a public demo because
the catalog can change. Gemma 4 Cloud is listed with per-token prices and is
not configured as a fallback. Ollama's pricing page says monthly resets apply
to included credits on paid subscriptions; it does not describe a universal
monthly free allowance. If Beam is unavailable, the app reports the
critique/chat as unavailable rather than switching to a paid model. Add other
fallbacks only after confirming they are free for your account.

Sources: [Beam model listing](https://ollama.com/library/beam) and
[Ollama pricing and usage FAQ](https://ollama.com/pricing).

Example shell configuration:

```sh
export OLLAMA_API_KEY='your-key'
# Optional: override the default with other models confirmed free in your account.
# export NUTRISENSE_CHAT_MODELS='beam:cloud,another-free-model'
```

Restart the FastAPI process after changing these values. With no API key,
meal analysis still works and the result page shows that the critique service
is unavailable. If `NUTRISENSE_CHAT_MODELS` is omitted, the backend tries
`beam:cloud`.

## Data sent to Ollama

The backend sends detected food labels, estimated grams, available energy and
protein estimates, component provenance, and assumptions. It omits the analysis
verdict so compliance scores do not influence meal advice.
It does not send the meal photo, student name, or local chat history beyond the
last four turns. Model output is advisory, is limited to the analyzed meal,
and should not be treated as medical advice. Nutrition values may be assumed
or incomplete, and the system has not been validated as a production nutrition
advisor.

Critique and chat endpoints use a 35-second timeout per model and try up to
three configured models in order. If a model reaches its output limit, the
backend retries once with twice the token budget. A user can retry an
unavailable automatic critique. Follow-up messages are saved only after a
successful model reply.
Ollama Cloud does not currently support structured outputs, so the critique
asks for JSON in its prompt and validates the returned fields in the backend
instead of sending the `format` option ([Ollama structured outputs docs](https://docs.ollama.com/capabilities/structured-outputs)).
