# CivicShield AI

**Predict Risks. Prevent Disasters.** A local civic reporting and flood-risk coordination application for a simulated Lahore municipal environment.

React + TypeScript + Vite frontend, Python FastAPI backend, PostgreSQL persistence, authenticated image storage, explainable numerical risk scoring, and three cooperating specialist agents. This project is independent of PyaraSaghar. No repository push or public deployment is part of this delivery.

## Civic Atlas interface

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

The Desktop `CivicShieldAI` folder contains **Launch CivicShieldAI.lnk**, a `Project` link to the actual source folder, and a project ZIP. Double-click the launcher to start services and open the app. Runtime logs are in `.runtime`. PostgreSQL listens only on `127.0.0.1:54329`.

## Fresh Windows installation

Requires Node.js 22+, Python 3.10+, PowerShell, and internet access for packages. Run:

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
- A real server-side OpenAI Responses vision adapter validates structured model output before applying allowed classification fields. Set `OPENAI_API_KEY` locally and `OPENAI_MODEL` to a supported image-capable model. Never put keys in frontend code or paste them into chat. Live provider access is an external dependency and is not claimed verified without a successful credentialed call.
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
