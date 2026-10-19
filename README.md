# CivicShield AI

**Predict Risks. Prevent Disasters.**

CivicShield AI is a civic reporting and flood-risk coordination platform. Citizens report hazards with a photograph, an AI vision model helps identify the hazard, authorities coordinate field teams, and an explainable risk model highlights areas where flooding is more likely. It is built and demonstrated for a simulated Lahore, Pakistan municipal environment.

| | |
|---|---|
| **Status** | Working prototype using clearly labeled synthetic demonstration data |

> **Important:** risk scores are planning heuristics, not calibrated probabilities or official warnings. CivicShield does not dispatch emergency services. Every AI suggestion requires a human decision.

---

## Table of Contents

1. [Problem Statement and Solution](#problem-statement-and-solution)
2. [Technology Stack](#technology-stack)
3. [Setup and Installation Instructions](#setup-and-installation-instructions)
4. [AI Methodology and Implementation](#ai-methodology-and-implementation)
5. [AI Model Names and API Usage](#ai-model-names-and-api-usage)
6. [Product Screenshots](#product-screenshots)
7. [Team Member Contributions](#team-member-contributions)

---

## Problem Statement and Solution

### The problem

Cities such as Lahore face recurring monsoon flooding and everyday civic hazards: blocked drains, rising water, open manholes, exposed electrical cables, uncollected waste and faulty traffic signals. Reporting these problems is slow and unstructured:

- Reports arrive as vague text with no photo, no exact location and no urgency.
- The same hazard is reported many times, while others are missed.
- Authorities have no single view that connects incidents, rainfall and the areas most at risk.
- Field workers receive instructions without evidence, and citizens never learn what happened.

### The solution

CivicShield AI connects the full lifecycle, from a citizen's photo to a verified fix.

| Role | What they can do |
|---|---|
| **Citizen** | Upload or take a photo, review the AI's detection, confirm the location (GPS, map pin or manual coordinates), optionally add a description, track the report, and view local weather and plain-language flood precautions. |
| **Authority** | See a command centre with an interactive map and priority queue, review AI suggestions, assign a whole team or one worker, choose to **share location only** or **share the complete report**, and approve or return completed work. |
| **Worker** | See assigned jobs and submit a completion photo with a note. |
| **Administrator** | Manage users, roles, departments, teams and flood-risk zones. |

Key capabilities:

- **Photo-first reporting** where an AI vision model analyses the real image bytes, validates the result, and falls back safely to human review if the model fails.
- **Duplicate screening** that flags nearby, recent reports of the same kind without merging them automatically.
- **Explainable flood-risk scoring** by zone, combining rainfall forecast, recent rainfall, blocked drains, water incidents and flood history.
- **Three cooperating specialist agents** (civic intelligence, disaster risk, response coordination) whose decisions are stored and visible.
- **Role-based privacy** enforced by the API across reports, photos, notes, history and notifications.
- **Evidence-based closure**: a worker's completion photo is reviewed by an authority before an incident is closed.

---

## Technology Stack

### Frontend

| Area | Technology |
|---|---|
| Framework | React 19, TypeScript 5.9 |
| Build tool | Vite 7 |
| Styling | Tailwind CSS 4, custom design system, self-hosted Manrope and IBM Plex Mono fonts |
| Data fetching | TanStack Query 5 |
| Routing | React Router 7 |
| Maps | Leaflet, React-Leaflet (OpenStreetMap tiles) |
| UI components | Radix UI Dialog, Sonner (toasts), Lucide icons |
| Testing | Vitest, Testing Library, Playwright (end-to-end) |

### Backend

| Area | Technology |
|---|---|
| Framework | Python 3.12, FastAPI, Uvicorn |
| Database | PostgreSQL 17, SQLAlchemy 2 (psycopg2) |
| Validation | Pydantic 2 |
| Authentication | JWT (HS256, 8-hour expiry) with PyJWT; PBKDF2-SHA256 password hashing (600,000 iterations) |
| Image handling | Pillow (images are re-encoded before storage) |
| HTTP client | httpx |
| Testing | pytest |

### External services

| Service | Purpose |
|---|---|
| Google Gemini API (default) | Photo hazard analysis. Other providers are supported (see below). |
| Open-Meteo | Rainfall, current weather and 7-day forecast. No API key required. |
| OpenStreetMap tiles | Map base layer |

### Infrastructure

- **Frontend hosting:** Vercel
- **Backend hosting:** Render (web service) with Render PostgreSQL
- **Containers:** Docker and Docker Compose (PostgreSQL, FastAPI, nginx)

### Project structure

```
CivicShieldAI/
├── backend/            FastAPI app, models, AI/vision adapters, risk engine, tests
│   └── app/            main.py, intelligence.py, vision.py, citizen_weather.py, ...
├── frontend/           React + Vite single-page application
│   └── src/            pages/, components/, lib/
├── database/           SQL schema (001), synthetic seed (002), migration (003)
├── docs/               Architecture, AI documentation, test report, design assets
├── scripts/            Windows setup/start scripts and vision-provider check
├── tests/              Playwright end-to-end tests
├── docker-compose.yml
└── CONTRACT.md         API contract and persisted lifecycle
```

---

## Setup and Installation Instructions

### Prerequisites

- Node.js 22 or later
- Python 3.12 (3.10+ works for local development)
- PostgreSQL 15 or later (or Docker)
- A Gemini API key (optional but required for photo analysis). Without one, the app still runs and reports are routed to human review.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/CivicShieldAI.git
cd CivicShieldAI
```

### 2. Option A: Run locally (Linux, macOS, Windows)

**Create the database**

```sql
CREATE USER civicshield WITH PASSWORD 'choose_a_strong_password';
CREATE DATABASE civicshield OWNER civicshield;
```

**Configure the environment.** Copy `.env.example` to `.env` in the project root and edit it:

```env
DATABASE_URL=postgresql+psycopg2://civicshield:choose_a_strong_password@127.0.0.1:5432/civicshield
JWT_SECRET=<random string of at least 32 characters>
DEMO_MODE=true
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VISION_PROVIDER=gemini
GEMINI_API_KEY=<your key>
GEMINI_MODEL=<an image-capable Gemini model available to your account>
```

Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Start the backend**

```bash
cd backend
python -m venv ../.venv
source ../.venv/bin/activate          # Windows: ..\.venv\Scripts\activate
pip install -r requirements-lock.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Tables are created automatically at startup. Check `http://127.0.0.1:8000/api/health`.

**Start the frontend** (in a second terminal)

```bash
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. In development, Vite proxies `/api` to the backend on port 8000.

> **Windows shortcut:** `.\scripts\setup-local.ps1` followed by `.\scripts\start.ps1` installs dependencies, creates a local PostgreSQL cluster and starts both servers. `.\scripts\stop.ps1` stops them.

### 3. Option B: Run with Docker

```bash
cp .env.docker.example .env.docker
# Edit .env.docker: set POSTGRES_PASSWORD, JWT_SECRET (different values) and your API key
docker compose --env-file .env.docker up --build -d
```

- Application: http://localhost:8080
- API docs: http://localhost:8001/docs

### 4. Demonstration accounts

Available only when `DEMO_MODE=true`. The login page then shows one-click demo buttons.

| Role | Email | Password |
|---|---|---|
| Citizen | citizen@civicshield.demo | CivicDemo!2026 |
| Authority | authority@civicshield.demo | CivicDemo!2026 |
| Worker | worker@civicshield.demo | CivicDemo!2026 |
| Administrator | admin@civicshield.demo | CivicDemo!2026 |

**Never enable `DEMO_MODE` for real data.** The demo password is public. For a real deployment, set `DEMO_MODE=false` and create the first administrator:

```bash
cd backend
python -m app.create_admin
```

### 5. Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL URL, must start with `postgresql://` or `postgresql+psycopg2://` |
| `JWT_SECRET` | Yes | At least 32 random characters; the app will not start without it |
| `CORS_ORIGINS` | Yes | Comma-separated list of allowed frontend origins (no trailing slash) |
| `DEMO_MODE` | No | `true` seeds synthetic demo data and demo accounts (default `false`) |
| `VISION_PROVIDER` | No | `gemini` (default), `openai`, `anthropic`, `huggingface`, `openai_compatible`, `ollama` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | For Gemini | Server-side key and model name |
| `VISION_MODEL`, `VISION_API_KEY`, `VISION_ENDPOINT` | No | Generic overrides for the selected provider |
| `VISION_FALLBACK_*` | No | Optional second provider used if the first fails |
| `VISION_TIMEOUT_SECONDS` | No | Per-request timeout, 5 to 90 (default 40) |
| `WEATHER_REFRESH_MINUTES` | No | Background weather refresh interval (default 30) |
| `UPLOAD_DIR` | No | Where photos are stored. Use a persistent disk in production. |
| `VITE_API_URL` | Frontend, production | Backend origin, e.g. `https://YOUR-API.onrender.com` (no trailing slash). Leave empty in local development. |

Never place API keys in a `VITE_*` variable; those are exposed to the browser.

### 6. Production deployment (Render + Vercel)

**Backend on Render**

1. Create a Render PostgreSQL database and copy its Internal Database URL.
2. Create a **Web Service** from this repository with these settings:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements-lock.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/api/health`
3. Add the environment variables from the table above (`DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `DEMO_MODE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `PYTHON_VERSION=3.12.8`).

**Frontend on Vercel**

1. Import the repository and set Root Directory to `frontend` (framework preset: Vite).
2. Add `VITE_API_URL` pointing to your Render service, then deploy.
3. Copy the Vercel URL into the backend's `CORS_ORIGINS` and redeploy the backend.

Render's free tier spins down after inactivity, uses an ephemeral filesystem (uploaded photos are lost on restart) and expires free databases after 30 days. Use a paid instance with a persistent disk (`UPLOAD_DIR`) for real use.

### 7. Run the tests

```bash
# Backend (uses an isolated test database; see docs/test-report.md)
python -m pytest backend/tests -q

# Frontend unit tests and production build
cd frontend
npm test
npm run build

# End-to-end browser tests (frontend and API must be running with DEMO_MODE=true)
cd ..
npm ci
npx playwright install chromium
npm run test:e2e
```

---

## AI Methodology and Implementation

CivicShield uses AI where it adds value (understanding photos) and deterministic, inspectable logic where accuracy and accountability matter (risk scoring). Every AI output is validated and requires human review.

### 1. Photo hazard analysis (vision model)

1. A citizen uploads a photo. The backend re-encodes it with Pillow and stores it.
2. The **actual image bytes** are sent to the configured vision model over the provider's API, with instructions to return structured JSON (hazard category, severity cues, description, suggested department).
3. The response is **validated against a Pydantic schema** (`HazardAnalysis`). Invalid or malformed output is rejected.
4. The citizen sees the result and can correct it before submitting.
5. If the provider fails, times out or is not configured, the report is **not blocked**. It falls back to deterministic text rules, clearly marked `image_analyzed=false`, and is sent for human review.

Safeguards: API keys never reach the browser, model output cannot call tools or write arbitrary database records, redirects and query-string credentials are rejected for custom endpoints, and an optional second provider can be configured as a fallback.

### 2. Duplicate screening

Candidate duplicates must share the suggested category, be within **180 m**, be within **7 days**, and still be unresolved. A weighted screening score is calculated:

| Factor | Weight |
|---|---|
| Category match | 0.25 |
| Proximity | 0.35 |
| Recency | 0.20 |
| Text similarity (Jaccard) | 0.20 |

Scores of 0.55 or higher are suggested to an authority. These are screening weights, not probabilities, and reports are never merged automatically.

### 3. Flood-risk scoring (numerical model)

For each circular Lahore zone:

```
score = 100 × (0.42 × forecast/60 + 0.18 × recent/40 + 0.22 × drains/3 + 0.10 × water/3 + 0.08 × history/10)
```

Each term is capped at 1. Rainfall is in millimetres; drain and water counts include only unresolved flood-related incidents inside the zone.

| Score | Level |
|---|---|
| Below 35 | Low |
| 35 to 64.9 | Moderate |
| 65 and above | High |

If rainfall windows are missing or weather data is stale (older than 6 hours by default), the result is **Insufficient Data** rather than a guess. Weights and thresholds are configurable and validated. Every assessment stores its weather source, retrieval time, contributing incidents, model version and limitations.

### 4. Specialist agent workflow

| Agent | Responsibility |
|---|---|
| **Civic Intelligence Agent** | Reads the report and photo evidence, classifies the hazard, screens duplicates, suggests a department. |
| **Disaster Risk Agent** | Reads the computed score and provenance, identifies vulnerable locations, explains missing information. It explains the model's output and never invents scores. |
| **Response Coordinator Agent** | Combines both outputs, raises flood-related priority when the zone is High, and proposes a department and action. |

The agents have scoped tools, exchange validated structured results, and store their inputs, outputs and a decision summary. The coordinator has **no dispatch or assignment tool**; recommendations stay Pending until an authority approves, rejects or overrides them.

### 5. Known limitations

- Risk scores are planning heuristics and have not been validated against real flood outcomes.
- The model does not include terrain, drainage capacity, soil moisture or uncertainty intervals.
- Past rainfall is modeled data from Open-Meteo, not rain-gauge observations.
- Zone history and seeded incidents are synthetic and labeled as such.
- Live vision inference depends on your provider account and configuration. Run `python scripts/check_vision.py --image <photo>` to verify it works before relying on it.

More detail: [`docs/INTELLIGENCE.md`](docs/INTELLIGENCE.md), [`docs/vision-providers.md`](docs/vision-providers.md), [`docs/architecture.md`](docs/architecture.md).

---

## AI Model Names and API Usage

### Vision (photo analysis)

The provider and model are chosen by environment variables, so you can switch without changing code.

| Provider | `VISION_PROVIDER` | Model variable | API endpoint |
|---|---|---|---|
| **Google Gemini (default)** | `gemini` | `GEMINI_MODEL` (default in `.env.example`: `gemini-3.8-flash`) | `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` |
| OpenAI | `openai` | `OPENAI_MODEL` | `api.openai.com/v1/responses` |
| Anthropic Claude | `anthropic` | `ANTHROPIC_MODEL` | `api.anthropic.com/v1/messages` |
| Hugging Face | `huggingface` | `HF_MODEL` | `router.huggingface.co/v1/chat/completions` |
| OpenAI-compatible server | `openai_compatible` | `COMPATIBLE_MODEL` | Custom (`COMPATIBLE_ENDPOINT`) |
| Ollama (local, no cloud key) | `ollama` | `OLLAMA_MODEL` | `http://127.0.0.1:11434/api/generate` |

Choose a model that supports **image input** and structured output in your account. The application never silently substitutes a different model. Model availability changes over time, so confirm the exact identifier in your provider's documentation before deploying.

### How the API is used

- **Request:** one call per photo, with the image sent inline as Base64 plus a structured-output instruction. Timeout is `VISION_TIMEOUT_SECONDS` (5 to 90, default 40).
- **Response handling:** parsed and validated with Pydantic; invalid output triggers the fallback provider (if configured), then the deterministic text fallback.
- **Cost and privacy:** each analysed photo is sent to the selected provider and may incur charges. Keys are stored only in backend environment variables.
- **Health check:** `GET /api/health` reports whether a vision provider is configured. "Configured" does not guarantee a successful call.

### Weather and forecast (no AI model)

[Open-Meteo](https://open-meteo.com/) supplies the preceding and next 24-hour precipitation, current conditions and the 7-day forecast. No key is required. Weather is refreshed on a schedule (`WEATHER_REFRESH_MINUTES`) and on demand.

### Application API

The backend exposes a REST API under `/api` with interactive documentation at `/docs`. Main areas: authentication, incidents, uploads, assignments, risk zones, agent runs, notifications, citizen weather and alerts. See [`CONTRACT.md`](CONTRACT.md) and [`docs/api.md`](docs/api.md).

---

## Product Screenshots

### Citizen

| Home | Report a hazard |
|---|---|
| ![Citizen home on mobile](docs/redesign/qa/citizen-390.png) | ![Citizen report form on mobile](docs/redesign/qa/citizen-report-390.png) |

### Authority command centre

![Authority command centre](docs/redesign/qa/authority-1440.png)

### Interactive map with risk layers

| Incident and risk layers | Selected incident |
|---|---|
| ![Map layers](docs/redesign/qa/map-layers-1440.png) | ![Selected incident](docs/redesign/qa/map-selected-incident-1440.png) |

### Worker and administrator

| Worker | Administrator |
|---|---|
| ![Worker view](docs/redesign/qa/worker-1440.png) | ![Administrator view](docs/redesign/qa/admin-1440.png) |

Additional screenshots and the design process are in [`docs/redesign/`](docs/redesign/).

---

## Team Member Contributions

> Replace the placeholders below with your real team details before submitting.

| Member | Role | Contributions |
|---|---|---|
| **Your Name** | e.g. Full-stack developer | e.g. FastAPI backend, database schema, authentication, deployment |
| **Member 2** | e.g. Frontend developer | e.g. React interface, map, responsive design |
| **Member 3** | e.g. AI / ML engineer | e.g. vision provider integration, risk model, agent workflow |
| **Member 4** | e.g. QA and documentation | e.g. test suites, demo guide, documentation |

---

## Further Documentation

- [`CONTRACT.md`](CONTRACT.md): API contract and persisted lifecycle
- [`docs/architecture.md`](docs/architecture.md): components, orchestration, risk model, permissions
- [`docs/INTELLIGENCE.md`](docs/INTELLIGENCE.md): AI and risk model details and limits
- [`docs/vision-providers.md`](docs/vision-providers.md): provider configuration and diagnosis
- [`docs/demo-guide.md`](docs/demo-guide.md): a 3 to 5 minute demonstration script
- [`docs/test-report.md`](docs/test-report.md): executed test results
- [`database/README.md`](database/README.md): SQL initialization and migrations

## Disclaimer

CivicShield AI is a prototype. It makes no claim of forecast accuracy, municipal validation, emergency dispatch capability or government partnership. In an emergency, contact your local emergency services.