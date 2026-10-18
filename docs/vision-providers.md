# Photograph analysis: providers, configuration and diagnosis

CivicShield sends the actual uploaded photograph to a configured vision model.
It validates the response before displaying detection. Storing a photograph,
finding a keyword in a description, or having an API key does not prove that an
image model ran. If image understanding fails, the report remains available for
manual categorization and official review, with an understandable failure notice.

## Configure one provider

Native installation: edit **the project-root `.env`** and restart the backend.
The backend explicitly loads that file, including UTF-8 files with a BOM.
Existing shell/container variables take precedence. Do not create a second
`.env` inside `frontend` or put a private key in a `VITE_` variable.

Docker: edit `.env.docker`, then recreate the backend using the Compose file:

```powershell
docker compose --env-file .env.docker up -d --force-recreate backend
```

A container restart alone does not reload changed Compose environment variables.
Keep existing database and JWT settings. The following settings control only
image understanding; the reporting workflow, weather and risk engine do not
require paid AI credentials.

| Setting | Purpose |
| --- | --- |
| `VISION_PROVIDER` | `openai`, `gemini`, `anthropic`, `huggingface`, `openai_compatible` or `ollama`. Default: `openai`. |
| `VISION_MODEL` | Exact accessible image-capable model identifier for the chosen provider. |
| `VISION_API_KEY` | Private key for the primary provider, kept server-side. |
| `VISION_ENDPOINT` | Optional **complete request URL**. It is not a base URL; use the provider’s final endpoint. |
| `VISION_TIMEOUT_SECONDS` | Per-provider request timeout, 5–90 seconds; default 40. |
| `VISION_FALLBACK_PROVIDER` | Optional second provider, attempted only if the primary configuration or request fails. |
| `VISION_FALLBACK_MODEL` | Exact image-capable model for the fallback. |
| `VISION_FALLBACK_API_KEY` | Fallback’s own private key. The primary generic key is never reused for another provider. |
| `VISION_FALLBACK_ENDPOINT` | Optional complete fallback endpoint. |

Provider-specific aliases are accepted when the generic setting is absent:

| Adapter | Key alias | Model alias | Endpoint alias / default request URL |
| --- | --- | --- | --- |
| OpenAI Responses | `OPENAI_API_KEY` | `OPENAI_MODEL` | `OPENAI_RESPONSES_URL` / `https://api.openai.com/v1/responses` |
| Google Gemini generateContent | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | `GEMINI_MODEL` | `GEMINI_ENDPOINT` / `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` |
| Anthropic Messages | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | `ANTHROPIC_ENDPOINT` / `https://api.anthropic.com/v1/messages` |
| Hugging Face VLM chat | `HF_TOKEN` | `HF_MODEL` | `HF_ENDPOINT` / `https://router.huggingface.co/v1/chat/completions` |
| OpenAI-compatible VLM chat | `COMPATIBLE_API_KEY` | `COMPATIBLE_MODEL` | `COMPATIBLE_ENDPOINT`; no public default |
| Ollama generate | `OLLAMA_API_KEY` if required | `OLLAMA_MODEL` | `OLLAMA_ENDPOINT` / `http://127.0.0.1:11434/api/generate` |

The existing `OPENAI_API_KEY` and `OPENAI_MODEL` configuration remains supported.
The historical OpenAI default is retained for compatibility; explicitly select a
currently available model that your account can use. Model availability and image
support depend on the provider/account. The application does not silently replace
a selected model. Gemini, Anthropic, HF and local models need an explicit model.

### OpenAI example

```dotenv
VISION_PROVIDER=openai
OPENAI_API_KEY=YOUR_PRIVATE_KEY
OPENAI_MODEL=YOUR_ACCESSIBLE_IMAGE_MODEL
```

### Gemini primary and Anthropic fallback

```dotenv
VISION_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_KEY
GEMINI_MODEL=YOUR_ACCESSIBLE_GEMINI_VISION_MODEL
VISION_FALLBACK_PROVIDER=anthropic
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY
ANTHROPIC_MODEL=YOUR_ACCESSIBLE_CLAUDE_VISION_MODEL
```

### Local Ollama model

An installed, running Ollama service and a downloaded **vision-capable** model
are required separately. The application does not install or download models.

```dotenv
VISION_PROVIDER=ollama
OLLAMA_MODEL=YOUR_DOWNLOADED_VISION_MODEL
OLLAMA_ENDPOINT=http://127.0.0.1:11434/api/generate
```

In Docker Desktop, a host service is normally reachable from the container using
`http://host.docker.internal:11434/api/generate`; the service must accept that
connection. `127.0.0.1` inside a container refers to that container. Check available
memory and model requirements before loading a local model.

For a local compatible chat server, choose `openai_compatible`, configure the
**complete** `/v1/chat/completions` endpoint and an image-capable model. A key is
optional for loopback/`host.docker.internal` compatible servers. HTTPS is required
for remote endpoints. A trusted private HTTP server can be enabled explicitly
using `VISION_ALLOW_INSECURE_HTTP=true`; do not use that for public endpoints.
Endpoints with query-string credentials or embedded user/password are rejected.
Redirects are rejected rather than forwarding the photograph or credentials.

HF support is for conversational vision-language models through its documented
chat API, not arbitrary object-detection or image-generation endpoints. Compatible
VLM APIs vary in structured-output options. The request includes the schema in
its instructions and always validates locally; optionally enable
`VISION_COMPATIBLE_JSON_MODE=true` if that server supports JSON mode.

## Check what actually works

From the extracted project root, using the installed project environment:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_vision.py
```

This prints safe provider/model/endpoint-host configuration, key-presence
booleans and actionable configuration errors. **Configured is not verified.** No
credential, raw photograph, prompt or provider response body is printed.

For a real test, use a non-sensitive photograph of an actual civic issue:

```powershell
.\.venv\Scripts\python.exe .\scripts\check_vision.py --image C:\Photos\blocked-drain.jpg
```

That explicit command sends the image to configured provider(s). Check
`image_request.image_analyzed=true` and `status=success`. `status=irrelevant`
or `uncertain` means the model examined it but did not confirm a civic hazard;
take a clearer/relevant photograph or choose a manual category. Such results
must not be presented as successful issue detection.

In the app, a Citizen uploads or captures a photograph and requests analysis
before submitting. Successful and failed draft results are retained with the
attachment. On submission the backend reuses a matching saved draft, avoiding
a second paid request. Reuse requires the same file SHA-256 and provider/model/
endpoint/key configuration fingerprint. An official’s explicit re-analysis
requests a fresh provider call. Adding a key does not update old stored analysis.

## Understand failures

| Code | Meaning and action |
| --- | --- |
| `missing_key` / `missing_model` | The selected backend provider is incomplete. Configure it in the correct environment and restart/recreate the backend. |
| `authentication` | The provider returned 401/403. Check the key’s project, permissions, model access and billing/account restrictions. |
| `quota` | The provider reported quota/billing exhaustion. Generating a key alone does not supply API quota. |
| `rate_limit` | Requests are temporarily limited. Retry later or use an explicitly configured fallback. |
| `model_or_endpoint` | Provider returned 404. Check the exact model, account access and complete endpoint. |
| `unsupported_request` | Provider rejected the request/image; confirm a vision-capable model and correct adapter/endpoint. |
| `connection` / `timeout` | The backend cannot reach the provider or it did not finish in time. Check network/local service and limits. |
| `invalid_image` | File could not be decoded, is unsupported or exceeds limits. Upload a valid JPEG/PNG/WebP up to 8 MB and under 30 megapixels. |
| `invalid_output` / `incomplete_response` | Model output was malformed, incomplete or failed the safety/evidence contract. No detection is claimed. |

Only sanitized codes/messages are retained. The model must explicitly confirm
image analysis, relevance and concrete visible evidence; it cannot write records,
assign a crew, close a report or invent a calibrated confidence score. Officials
still verify the category, urgency and repair.

## Verification limits for this update

All adapter protocol tests use HTTP mocks to verify distinct request formats,
authentication, image bytes, response validation, fallback credential isolation,
irrelevant photographs and failures. Those tests do not prove account access or
real model accuracy. The project `.env` and shell checked during development did
not contain any configured cloud vision keys. A key reportedly configured on a
friend’s different PC cannot be inspected from this computer. The diagnostic
command reports the actual outcome on whichever PC runs it. Do not describe a
provider as live-verified unless a real request succeeded there.

## Primary API references

- [OpenAI image inputs](https://developers.openai.com/api/docs/guides/images-vision)
- [Gemini generateContent image request](https://ai.google.dev/gemini-api/docs/generate-content/text-generation)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)
- [Anthropic image content blocks](https://platform.claude.com/docs/en/build-with-claude/vision)
- [HF chat completion and VLM input](https://huggingface.co/docs/inference-providers/main/tasks/chat-completion)
- [Ollama generate images and JSON format](https://docs.ollama.com/api/generate)
