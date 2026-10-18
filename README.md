# CivicShield AI

**Predict Risks. Prevent Disasters.** A local civic reporting and flood-risk coordination application for a simulated Lahore municipal environment.

React + TypeScript + Vite frontend, Python FastAPI backend, PostgreSQL persistence, authenticated image storage, explainable numerical risk scoring, and three cooperating specialist agents. This project is independent of PyaraSaghar. This repository contains the authorized source update; no public application deployment has been performed.

## Civic Atlas interface

### Photo-first workflow update — 19 October 2026

Citizens now start with **Upload a photo** or **Take photo**, review the image-service
result before submission, confirm a GPS/map/manual location, and optionally add
a title or description. Photo-only reports are supported. Failed/unconfigured
image detection is clearly shown; reports can still be sent for human review.
The citizen home also links to real current/seven-day weather and readable local
waterlogging estimates and precautions. Officials retain technical risk tools.

Authorities can assign an entire team or a particular active worker, and choose
**Share location only** or **Share complete report**. The API enforces that choice
across report details, lists, photographs, notes, history and notifications.
Workers can submit a completion photo with an optional note directly from an
assignment. Authorities can approve/close it or return it for more work with fresh
evidence; citizens track the final status.

See [configuration and actual verification limits](docs/workflow-upgrade.md) and
[vision-provider setup](docs/vision-providers.md). No local vision runtime/model
or cloud provider key was available on this PC during verification; live image
understanding is not claimed tested. The application supports a configured local
Ollama or compatible vision server without changing the frontend.

The implemented redesign uses a forest navigation rail, warm paper canvas, locally packaged Manrope/IBM Plex Mono fonts, one operational summary rail, a large interactive map, an actionable priority queue, three distinct intelligence summaries, and a full-width incident ledger. Reporting, evidence, assignments, risk analysis, administrative tools, and notifications use the same visual system.

The map supports independent incident/flood-risk layers, severity filtering, keyboard marker selection, linked incident details, and restoring the operational extent. Risk zones preserve their stored radius with restrained transparent styling.

- [Selected direction and design contract](docs/redesign/design-direction.md)
- [Editable Figma screens and component library](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU)
- [Figma handoff](docs/redesign/figma-handoff.md)
- [Role navigation and retained capabilities](docs/redesign/role-navigation.md)
- [Rendered design verification](design-qa.md)

## Run on this Windows computer

The prepared installation has its own Python environment, PostgreSQL cluster, application database and test database. From this folder:

```powershell
.\scripts\start.ps1
```

- Frontend: http://127.0.0.1:5173
- Backend health: http://127.0.0.1:8000/api/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- Stop owned processes: `.\scripts\stop.ps1`

Desktop launchers created on the original development PC are optional and are not part of a fresh repository installation. Use the commands below on another computer. Runtime logs are in `.runtime`. The native PostgreSQL instance listens only on `127.0.0.1:54329`.

## Fresh Windows installation

Docker uses a separate `.env.docker` configuration and a running Docker Linux engine. It does not require host Python/Node installations. Container execution has not been verified on the development PC because no Docker engine is installed. For a local demo with the four demonstration accounts:

```powershell
.\scripts\configure-docker.ps1 -Demo
docker compose --env-file .env.docker up --build -d
```

Open `http://localhost:8080`; Docker API documentation uses `http://localhost:8001/docs`. Without `-Demo`, configuration defaults to production mode without public demo accounts. Keep real `.env` and `.env.docker` files private. Provider setup and verification limits are in [the current guide](docs/workflow-upgrade.md).

A fresh native Windows installation requires Node.js 22.20.x (the tested version), Python 3.10+, PowerShell, and internet access for packages. Clone or extract this repository first. Let setup generate `.env` rather than copying `.env.example` for this local installation. Run:

```powershell
.\scripts\setup-local.ps1
.\scripts\start.ps1
```

The setup script installs dependencies, verifies the integrity of a pinned Windows PostgreSQL binary package, initializes a password-protected local cluster and creates application/test databases. It generates local secrets only when `.env` is absent. It enables explicitly labeled demonstration data. Never copy that local configuration to a public server.

For an existing PostgreSQL instance or Linux/macOS: create a database and a dedicated role, create a Python virtual environment, install `backend/requirements-lock.txt` for the tested versions, copy `.env.example` to `.env` and configure it. Start the API from `backend` with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; run `npm ci` and `npm run dev -- --port 5173` in `frontend`. Database initialization happens during API startup. SQL initialization is also available under `database/`.

## Demonstration accounts

Available only when `DEMO_MODE=true`. Each role has a visible demo login button.

| Role | Email | Password |
|---|---|---|
| Citizen | citizen@civicshield.demo | CivicDemo!2026 |
| Authority | authority@civicshield.demo | CivicDemo!2026 |
| Worker | worker@civicshield.demo | CivicDemo!2026 |
| Administrator | admin@civicshield.demo | CivicDemo!2026 |

The worker belongs to the seeded sanitation response team. Newly registered accounts are citizens. Role changes, disabling users, organizational CRUD and zone configuration require an administrator. Passwords are hashed; authorization is enforced by the API.

## Intelligence and data provenance

- Civic Intelligence classifies **report text** using transparent rules by default. Uncertain cases remain subject to review. Photographs are retained but **not analyzed** without a configured vision provider.
- Server-side adapters support OpenAI Responses, Gemini, Anthropic, Hugging Face conversational vision, OpenAI-compatible services and local Ollama. Configure `VISION_PROVIDER`, `VISION_MODEL`, `VISION_ENDPOINT` and server-side credentials as needed; optional fallback has its own configuration. Each adapter sends actual image bytes and validates structured output. Never put keys in frontend code or paste them into chat. Live provider access is not verified until a real image call succeeds.
- Disaster Risk uses a numerical weighted model; the agent explains its output rather than inventing scores. Scores are heuristic indicators, not calibrated probabilities or official warnings.
- Response Coordinator consumes shared civic and disaster outputs to propose actions. Recommendations require a human decision. Agents cannot dispatch services or assign workers.
- Open-Meteo supplies modeled rainfall and forecasts when reachable. Failures and stale/missing data are recorded. Heavy rain, clear and missing-data controls inject **synthetic demonstration scenarios**. Historical counts and seed incidents are synthetic and visibly labeled.
- Leaflet loads map tiles from external providers. Locations remain editable through coordinates if tiles or GPS are unavailable.

## Test and build

```powershell
# Backend tests use the isolated civicshield_test PostgreSQL database.
.\.venv\Scripts\python.exe -m pytest backend/tests -q
# Production frontend build
Push-Location frontend
npm test
npm run build
Pop-Location
# Browser tests require running local frontend/API and explicit demo mode.
npm ci
npx playwright install chromium
npm run test:e2e
```

See `docs/test-report.md` for executed results and `docs/completion-matrix.md` for tested scope. Browser tests create clearly named test records and use the same real API/database as the UI.

## Further documentation

- `CONTRACT.md` — API contract and persisted lifecycle.
- `docs/architecture.md` — components, orchestration, risk model and permissions.
- `docs/demo-guide.md` — a practical 3–5 minute demonstration.
- `docs/deployment.md` — container deployment preparation and required production configuration.
- `database/README.md` — SQL initialization and seed/reset instructions.

The master build prompt and complete product redesign brief govern this implementation. The three original proposal/transcript files referenced in the master prompt were not attached.
