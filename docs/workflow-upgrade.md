# Photo reporting, assignments and local safety update

Verification date: **19 October 2026 (Asia/Karachi)**. Everything remains local.
These local verification results preceded the subsequently authorized GitHub source update. No public application deployment was performed.

## What was wrong

The previous workflow analyzed photographs only after report submission, required
written fields, and provided no citizen weather view. A configured vision failure
fell back to text rules, which could be mistaken for image understanding. The
previous authority assignment could not restrict a worker to location-only data.

This PC's root `.env` is loaded, but it contains no working vision credential.
No Ollama/LM Studio/llama server, downloaded model in the usual model directories,
or listening local vision service was found. Thus the friend's exact authentication,
quota or model failure cannot be established from this computer. Run the safe
diagnostic on that PC to identify it; never share the private key.

## What each person does now

| Account | Purpose and shortest workflow |
| --- | --- |
| Citizen — Ayesha Khan | Start with **Upload a photo** or **Take photo**. Read the actual detection result or unavailable notice. Correct the category if needed, confirm location, and send. Title and description are optional with a photo. Follow the reference in **My reports** and **Notifications**. View **Local weather** and **Disaster alerts & predictions**. |
| Authority — Omar Farooq | Review the photograph, analysis, location and report. In **Response**, choose a team or named worker and either **Share location only** or **Share complete report**. Review the worker's completion photograph. Enter a verification decision, then **Approve repair & close** or **Return for more work**. |
| Worker — Ali Hassan | Open assigned tasks. Read the location and information the authority shared. Navigate to the location, do the repair, upload **Completion evidence**, and choose **Submit completion**. A completion note is optional; Accept/Start remain available but are not required before direct completion. Corrections require another photograph. |
| Administrator | Maintain users, roles, active teams, departments and planning zones. Administrative operations remain separate from day-to-day report review. |

Demo emails are `citizen@civicshield.demo`, `authority@civicshield.demo`,
`worker@civicshield.demo`, `admin@civicshield.demo`; demo password is
`CivicDemo!2026`. These accounts are for explicit `DEMO_MODE=true` only.
The worker is in **Drainage Response · Central**, in **Water & Sanitation**.
Assign that team or that worker when demonstrating the example drainage repair.

**Resolved** means the worker submitted completion for verification. **Closed**
means the authority approved it. No model automatically assigns a worker or closes
a complaint. Reports, assignments, evidence, decisions and notifications persist
in PostgreSQL and authenticated upload storage.

## Vision configuration and evidence

See [vision-providers.md](vision-providers.md) for complete provider-specific setup.
The separate adapters implement OpenAI Responses, Gemini generateContent,
Anthropic Messages, conversational Hugging Face/OpenAI-compatible chat, and Ollama
generate. These are configurable service options, not six installed AI models.

For an **already installed and running local vision model**, edit root `.env`:

```dotenv
VISION_PROVIDER=ollama
OLLAMA_MODEL=YOUR_INSTALLED_VISION_MODEL
OLLAMA_ENDPOINT=http://127.0.0.1:11434/api/generate
```

For a local OpenAI-compatible vision server, use `VISION_PROVIDER=openai_compatible`,
`VISION_MODEL`, and a complete `VISION_ENDPOINT` ending in `/v1/chat/completions`.
Loopback local servers do not require a cloud key. A text-only model cannot analyze
images. No local model was installed/downloaded as part of this update: none was
available, and the PC had about 1.7 GB free system RAM when checked (16 GB total,
Quadro M1200 4 GB VRAM). Local inference remains unverified.

Restart the backend after changing `.env`. For Docker, set `.env.docker` and
recreate the backend; host Ollama normally needs
`http://host.docker.internal:11434/api/generate`. Compose now forwards generic,
provider-specific and fallback configuration. Do not use container loopback to
refer to a service on the host.

```powershell
.\.venv\Scripts\python.exe .\scripts\check_vision.py
# Explicit real provider test, after configuration:
.\.venv\Scripts\python.exe .\scripts\check_vision.py --image C:\Photos\civic-issue.jpg
```

Only an actual validated `status=success`, `image_analyzed=true` response counts
as successful civic issue detection. Configured, uploaded, text classification,
irrelevant, uncertain and failed are different states. Image bytes are decoded,
limited and sent server-side. Output must include concrete visual evidence and
relevance. Errors are sanitized; private keys stay out of frontend code and logs.
An explicitly configured fallback uses its own credentials. Saved draft analysis
is reused on initial submission only when its image/configuration fingerprints
match. An authority's explicit re-analysis requests a fresh provider call.

## Weather, risk and limitations

`/api/citizen/weather` retrieves real current temperature, condition, humidity and
wind plus seven daily temperature ranges, rain probabilities, precipitation and
wind forecasts from Open-Meteo. It caches briefly and displays an explicit
unavailable state on connection or invalid-data failure. It never fills gaps with
LLM-generated weather. The current area is shown; citizens can choose GPS, a map
point or manual coordinates.

`/api/citizen/alerts` uses live preceding/next 24-hour rainfall with aggregate
unresolved local drainage/water reports and configured history for a readable
waterlogging **planning estimate**. Missing rainfall means **Insufficient Data**.
Outside configured zone coverage, no local score is issued. Other citizens'
identities, photos, descriptions and report IDs are never exposed. Demo incident
and historical inputs remain labeled. Rain, heat and wind precautions are simple
forecast rules, not confirmed disaster predictions.

There is **no connected official warning feed**. That limitation is shown in the
citizen interface. The app does not dispatch emergency crews and the flood score
is neither a calibrated probability nor a hydrological model. Official notices
must come from the relevant authorities.

The three specialist components remain distinct: Civic Intelligence uses the
configured vision model or transparent text rules; Disaster Risk computes an
explainable weighted score; Response Coordinator proposes rule-based response
actions for human approval. They are not three independently trained LLMs.

## Database and preserved data

The transactional, idempotent `003_photo_first_workflow.sql` migration adds
`attachments.analysis`, `assignments.sharing_scope` (existing rows default to
`full_report`), and nullable `assignments.worker_id` with a foreign key. It adds a
sharing-scope constraint. FastAPI startup applies the bundled equivalent after
creating tables. Docker does not depend on an external SQL directory at runtime.
Migration tests create a legacy schema, apply the migration twice, and verify
original rows survive. Before native startup, a local record backup was saved
under `.runtime/backups`; uploads were retained.

Location-only restrictions are enforced in API projections and download checks,
including lists, dashboard activity, attachments, notes, audit/history,
recommendations, old assignment instructions and notifications. Selecting an
individual worker excludes other members of the same team. The worker cannot
change their recipient or expand their sharing scope.

## Main implementation files

- `backend/app/vision.py`, `config.py`, `intelligence.py`: adapters, validation,
  diagnostics, real-image requests and saved-preview reuse.
- `backend/app/main.py`, `services.py`, `schemas.py`, `models.py`, `migrations.py`:
  draft analysis, optional reporting fields, category review, worker recipients,
  sharing enforcement, evidence/verification and safe schema upgrade.
- `backend/app/citizen_weather.py`: live weather, readable risk and precautions.
- `frontend/src/components/ReportForm.tsx`, `IncidentDetails.tsx`, `Map.tsx`,
  `pages/Dashboard.tsx`, `pages/CitizenWeather.tsx`, `App.tsx`, `styles.css`:
  integrated role workflows and responsive citizen views.
- `.env.example`, `.env.docker.example`, `docker-compose.yml`, provider guide and
  diagnostic script: configurable native/container deployment preparation.
- `backend/tests/test_vision_providers.py`, `test_photo_first_workflow.py`,
  `test_citizen_weather.py`, frontend tests, and browser acceptance suites:
  protocol/error/privacy/persistence and real UI lifecycle checks.

## Verification status

The complete backend suite passed **128 tests** on an isolated PostgreSQL test
database. Frontend tests passed **19 tests** and the TypeScript/Vite production
build passed. Provider protocol tests use HTTP mocks; they do not establish live
model access or accuracy. The running weather API was successfully checked
against actual Open-Meteo current/seven-day data on 19 October 2026.

Browser results and final handoff status are recorded in [test-report.md](test-report.md).
Docker Compose configuration validates, including local-provider variables;
Docker engine/container execution remains unverified because Docker Desktop/WSL
is not installed. Physical mobile camera/GPS accuracy, real provider inference,
official emergency-feed integration and public deployment are not claimed tested.

## Real problem addressed

Citizens often report damaged roads, blocked drains or exposed hazards through
disconnected channels, then lose track of the complaint. Authorities lack a
consistent queue and workers lack clear tasks or a shared completion record.
CivicShield connects the photo and location to review, assignment, repair evidence,
verification and a visible final status. Weather and local drainage evidence help
plan attention before rainfall. Success in real use depends on an actual local
authority operating the workflow and verifying repairs; software alone cannot
perform the field work.
