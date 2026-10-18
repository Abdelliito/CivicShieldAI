# Executed verification report

## Current update — 19 October 2026

| Check | Executed result |
| --- | --- |
| Complete backend suite | **128 passed**, isolated PostgreSQL `civicshield_test`; one dependency deprecation warning. |
| Frontend unit suite | **19 passed**, four files including photo-preview safeguards, interrupted session restoration and expired-token handling. |
| Production build | TypeScript/Vite **passed**; 1,755 modules, JS 645.25 kB (195.07 kB gzip), CSS 91.26 kB. |
| Browser acceptance | **36 unique checks have passing final results**, across the combined and focused reruns below. Actual frontend/API/PostgreSQL, all four roles and 1440/1280/768/390px views. |
| Live weather | Actual Open-Meteo current conditions and seven forecast dates retrieved; desktop/mobile weather, rain chance, humidity, wind and sourced risk advice passed. |
| Data migration | All **39 original incidents/reports**, 13 users, 22 assignments and 29 attachment rows retained. Legacy-schema upgrade tested twice for idempotence. Private backup under `.runtime/backups`; uploads retained. |
| Stop/start | All three owned services stopped, including the Windows Python child process. PostgreSQL, backend and frontend restarted; frontend HTTP 200 and database health connected. |
| Live vision | **Not verified**. No cloud vision key or installed/running local vision model available. **38 provider/config tests use HTTP mocks**, not a real model. Detection-unavailable UI and human-review reporting tested. |
| Docker | Compose configuration/interpolation passed, including local-provider variables. No Linux engine: image builds and container execution **not tested**. No public application deployment. GitHub source synchronization was authorized separately after these local checks. |

The combined 32-check browser run passed 29 and exposed three assertions using
old headings/status labels. Updated those assertions and reran the retained full
report lifecycle, registration/login/session/notification checks, and duplicate
review/classification/note/reassignment/reversible-archive journey to passing results.
The four new checks passed: photo-only location-only direct-worker lifecycle with
optional notes, corrections/fresh evidence/closure; live weather and readable
alerts at desktop and 390px; and controlled weather outage/GPS-denial handling.

Actual fixes found during integration include report-edit category validation,
file picker mounting after the modal portal, and valid saved credentials being
erased after an interrupted restoration request. The report-edit browser test
now waits for its successful PATCH and dialog closure before reloading, so text
inside an unsaved textarea cannot pass as database persistence.

Raw evidence lives outside the source project under `E:/Desktop/CivicShieldAI-QA/`:
`final/test-results` (29 combined passes), `final-rerun-fixed/test-results`
(three weather/failure checks), `lifecycle-verified/test-results` (three passing
lifecycle/auth journeys), and `duplicate-final/test-results` (final passing archive
journey). Screenshots are in `upgrade/`. Earlier failed/interrupted traces are
retained for diagnosis, excluded from pass counts and the source ZIP.

The dedicated Browser plugin was unavailable. Inspection used Codex's in-app
browser, with repository Playwright Chromium for repeatable acceptance as the
user requested. Physical phone camera/GPS accuracy and actual model inference
remain external checks. See [workflow/configuration/changed files](workflow-upgrade.md)
and [provider setup](vision-providers.md). Current notes supersede the older PDF
and historical test counts for the revised workflow.

## Historical verification — 17 October 2026

Date: **17 October 2026**. Windows, Node 22.20.0, Python 3.10.9, local PostgreSQL 18.4. React/Vite at `http://127.0.0.1:5173`; FastAPI at `http://127.0.0.1:8000`.

## Executed results

| Check | Result |
|---|---|
| Backend API, security, intelligence and scheduler | **70 passed**, including the new UTC/date-boundary regression; isolated PostgreSQL database. Final complete backend run 26.13 seconds. |
| Frontend unit/auth/component checks | **12 passed** across two files. |
| Browser acceptance | **32 unique checks passed after fixes and focused reruns**: the original 11 workflow journeys plus 21 redesign checks. No test was skipped. |
| TypeScript and production build | **Passed** with final source; Vite 1,754 modules, JS 620.22 kB before gzip 187.75 kB, CSS 78.82 kB before gzip 22.37 kB. Local fonts included. |
| Database persistence and SQL seed | API/browser journeys use the real persistent demonstration database. Standalone SQL scripts were verified during the original 16 October build in an isolated schema: 12 incidents, 4 roles, 52 risk assessments and valid constraints. No schema change was needed for the redesign. |
| Live Open-Meteo request | Verified during the original 16 October build; modeled rainfall parsed with provenance. Redesign checks use explicitly synthetic clear/heavy/missing scenarios. |
| Live vision provider | **Not verified**: no server-side provider credential configured. Request schemas, retries, validation and fallback have controlled-response tests. |
| Phone camera and GPS hardware | Camera capture attribute/file chooser/preview and simulated granted GPS/map selection tested. Physical phone camera/GPS accuracy is outside this Windows browser verification. |
| Containers and public deployment | **Not executed**: Docker unavailable during original setup. Dockerfiles, compose/nginx configuration and deployment instructions are prepared. No push or publication performed. |

## Browser evidence and rerun accounting

The latest result for every test is saved in [browser-verification-summary.json](redesign/browser-verification-summary.json). The final combined run passed 25 checks and exposed four 390px layout/navigation failures, an artifact-output collision in a concurrent rerun, and two long-journey timeouts. Fixed the real UI issues, isolated test output folders, and reran the seven affected checks. Six passed in the focused rerun. The full four-role reporting journey then passed separately in 1.6 minutes with a 180-second total budget; its assertions remain unchanged. Thus all 32 unique acceptance checks have a passing final result.

Local raw result files are retained under `.runtime/final-browser-results.json`, `.runtime/final-retry-results.json` and `.runtime/final-workflow-first.json`. They are excluded from the source ZIP along with traces/runtime data. The checked-in summary includes test names, statuses, durations and evidence-run filenames without credentials.

The standalone Browser skill was unavailable. Product inspection used Codex's in-app browser first; repeatable acceptance used the project's Playwright Chromium workflow, as explicitly requested. The frontend remained connected to the actual FastAPI/PostgreSQL application.

## Verified journeys

1. Citizen photograph/location/description submission, preview removal/replacement, reference creation, permitted editing and reload persistence; authority team assignment, note/evidence request; citizen additional evidence/reply; worker acknowledgement/start/completion evidence; authority verification/closure; citizen Closed status and notification.
2. Granted GPS, manual map selection and editable coordinates; reversible withdrawal/restore; saved photograph removal/replacement.
3. Persisted text, category, severity, status, zone and date filtering, empty state and clearing filters.
4. Incorrect login, citizen registration, protected-route redirect, expired-session recovery and notification read/unread.
5. Departments, teams, zones and users: create, inspect, edit, reload, deactivate and reactivate.
6. Clear/heavy/missing weather scenarios, independent risk changes, zone factors/provenance/history, recommendation approve/reject/override and three specialist execution logs.
7. Duplicate merge/separate/reject, justified classification/severity correction, note CRUD, assignment/reassignment/cancellation, rejection and reversible archive.
8. Desktop/mobile app rendering, visible API failure feedback, absence of local app-script errors/page exceptions and role-isolated reads.
9. Every authorized route for all four roles at 1440, 1280, 768 and 390px; heading bounds, contained page/table scrolling, mobile navigation and role-specific links.
10. The 390px report form: blank coordinate remains invalid, valid numeric input, explicit Take photo camera/file chooser, actual image preview, oversized replacement rejection preserving the prior preview, removal/replacement, Escape and focus return.
11. Incident/flood-risk layer toggles and real API marker/zone counts; keyboard incident selection with selected-state/context/detail tabs/focus return; actual zoom followed by Focus Lahore; keyboard risk-zone details with stored factors/provenance/history.

## Corrections made during integration

- Naive/date-only incident bounds now explicitly use UTC; explicit offsets remain unchanged. The regression forces a Karachi PostgreSQL session and tests UTC midnight/evening/next-day boundaries.
- Selected incident/risk details derive from current query records; unchanged geometry does not reset map pan/zoom.
- SVG markers/risk circles support keyboard activation; dialogs restore focus to actual HTML/SVG openers, including Strict Mode.
- The mobile drawer has inert hidden links, keyboard trapping/Escape and a visible close control.
- Table scroll containers now position visually hidden headers locally. This fixes 705px document overflow on 390px screens while preserving the table's own 730px scrollable width.
- Empty coordinate drafts no longer become zero; rejected replacement images preserve valid previews; preview URLs are cleaned up.
- Worker completion notes require ten trimmed characters before uploading evidence.

## Visual verification

Compared the selected Civic Atlas image with the actual authority render together, first at full view and then with normalized focused intelligence/table crops. Font, hierarchy, spacing, palette, images, icons, copy, state and responsive behavior were reviewed. Earlier typography, vertical-density and map-control findings were repaired. [design-qa.md](../design-qa.md) has **final result: passed**.

Final authority capture: CSS 1440x1024, approximately 1 DPR, capture 1425x1013, Manrope Variable confirmed and 15 loaded OSM tiles. Source 1487x1058 and implementation were normalized to 1440x1024 for comparison. User-visible records remain real API data; generated geography and invented timestamps were not copied.

- [Authority dashboard](redesign/authority-final-1440.png)
- [Administration and complete management navigation](redesign/admin-final-1440.png)
- [Citizen mobile report](redesign/citizen-form-final-390.png)
- [Citizen camera/location section](redesign/citizen-location-final-390.png)
- [Role/viewport evidence](redesign/qa/)
- [Editable Figma handoff](redesign/figma-handoff.md)

## Retained data and limits

All 12 original Lahore demonstration incidents remain visible. Fourteen exact generated reports from redesign verification were reversibly archived; test registration accounts/organizational records were deactivated, not purged. Original submissions, evidence and audit history remain. Cleanup manifests are local in `.runtime/redesign-test-record-manifest.json`, including prior-run records. Earlier build-test cleanup remains separately recorded.

The final local presentation uses a clearly synthetic heavy-rain scenario with stored provenance. Risk estimates are not official forecasts or calibrated flood probabilities. Civic Intelligence currently uses report-text rules, Disaster Risk uses the numerical weighted engine and Response Coordinator uses validated rule-based handoffs. These are three working specialist components, not three verified live language models. Authentic municipal history, physical device accuracy, credentialed image understanding and a public container host remain external verification limits.

No Git remote is configured. Nothing was pushed or published. The desktop source ZIP is rebuilt through `scripts/package_project.py`, checked for integrity, and excludes `.env`, dependencies, database files, uploads and runtime artifacts.
