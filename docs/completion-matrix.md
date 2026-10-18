# Completion matrix and evidence

## Current photo/workflow/weather update — 19 October 2026

This section supersedes older requirements and counts below. The current backend
suite passed **128**, frontend unit suite **19**, and **36 unique browser checks**
have passing final results after documented focused reruns. The production build
passed. See [current evidence](test-report.md) and [updated workflow/configuration](workflow-upgrade.md).

| Capability | Implementation and actual verification |
| --- | --- |
| Pre-submit photograph analysis | Actual bytes, provider-specific adapters, draft preview and fingerprinted reuse implemented and protocol-tested. **Real model inference is unverified: no key or installed local model available.** |
| Provider switching/fallback | OpenAI, Gemini, Anthropic, HF conversational vision, compatible chat and Ollama; environment configuration and isolated fallback credentials. 38 controlled HTTP/config tests passed, not six live services. |
| Photo-only report | Optional title/description, valid confirmed location, manual category correction, saved photo/reference/status. Backend and browser lifecycle passed. |
| Sharing and named recipients | Full report/location-only, team/named active worker; backend redaction, download restrictions and direct-recipient isolation passed. Location-only UI journey passed. |
| Completion/verification | Photo required, notes optional; direct completion, corrections with fresh evidence, authority approval and citizen Closed state passed. Existing Accept/Start/full-report flow retained. |
| Citizen weather/risk | Live current/seven-day weather verified on desktop/mobile; real rainfall with local aggregate planning estimate. Synthetic inputs, missing data, zone coverage and absent official warning feed explicit. |
| Records/CRUD | Additive idempotent migration and original data retention verified; role/admin CRUD and authenticated evidence retained and tested. |
| Deployment | Native stop/restart verified. Source-only packaging and Docker configuration prepared. **Containers/public deployment not tested or performed.** |

## Historical scope below



Audit date: **17 October 2026**. This matrix distinguishes implementation, executed backend checks, and browser acceptance. A source file or a written browser test is not evidence that its user journey passed.



Final acceptance: **70 backend tests, 12 frontend unit/component tests and 32 unique browser checks passed after fixes and focused reruns**. This includes the original 11 workflow journeys and 21 redesign checks. SQL scripts were executed against PostgreSQL during the original build; final Civic Atlas desktop/mobile screenshots were inspected. Commands and practical limits are in [test-report.md](test-report.md). Live vision and container deployment retain the explicit verification limits below.

The Civic Atlas redesign adds the map layers, severity filter, keyboard context and recenter controls alongside coherent role-specific styling. The Citizen form includes a Take photo camera/file-chooser path; its capture attribute, chooser and preview were exercised in the 390px browser test. Physical phone-camera hardware is not claimed verified. Administration remains Admin-only, with organizational CRUD workflows retained. See [role navigation](redesign/role-navigation.md) and [rendered design QA](../design-qa.md).



Evidence references:



- **API** â€” [backend/tests/test_api.py](../backend/tests/test_api.py), actual isolated PostgreSQL database; registration/permissions, report and attachment lifecycle, assignment completion/corrections, entity CRUD, status/history, notifications, risk and agent decisions.

- **Security** â€” [backend/tests/test_security_audit.py](../backend/tests/test_security_audit.py), actual isolated PostgreSQL database; current assignments, fresh evidence, deactivation constraints, ownership, consolidated incidents, notifications and no automatic assignment.

- **Intelligence** â€” [backend/tests/test_intelligence.py](../backend/tests/test_intelligence.py), validated schemas, numerical/heuristic tools, mocked provider boundaries and isolated unit persistence. Latest focused execution: **39 passed**.

- **Scheduler** â€” [backend/tests/test_scheduler.py](../backend/tests/test_scheduler.py), controlled provider integration with real PostgreSQL plus interval dispatch and historical geometry tests. Executed with the Intelligence suite: **42 passed** (3 Scheduler + 39 Intelligence), 11.93 seconds.

- **Browser** â€” [tests/e2e/workflow.spec.ts](../tests/e2e/workflow.spec.ts), running frontend, API and persistent local database; **11 journeys passed against the running frontend/API/PostgreSQL**.

- **Frontend** — `frontend/src/lib/api.test.ts` and `frontend/src/components/UI.test.tsx`; **12 passed**, including stale/aborted session requests, errors, upload validation, timestamp handling, accessible labels, pending controls and dialogs.

- **SQL** â€” [backend/export_sql.py](../backend/export_sql.py), [backend/verify_sql.py](../backend/verify_sql.py), [database/001_schema.sql](../database/001_schema.sql), [database/002_seed.sql](../database/002_seed.sql). Backend developer reported successful export/execution/constraint verification in generated temporary PostgreSQL schemas.



## Citizen portal



| Feature | Implementation and screen/API | Backend evidence | Browser status / limitation |

|---|---|---|---|

| Citizen registration, sign in/out, demo roles | Login screen; `/auth/register`, `/auth/login`, `/auth/me`; expiring JWT and password hashing | API authentication, strict citizen registration, own-record scope and disabled token tests | Passed browser registration, incorrect login, sign out, role switching and expired-session recovery |

| Own dashboard and reports | Overview and My reports; `/dashboard`, scoped `/incidents` | API dashboard totals, citizen scope and detail reads | Passed browser acceptance |

| Create description/location report and reference | New report dialog; `POST /reports`; real Incident and original Report rows | API validation, persistence and lifecycle tests | Passed browser submission, reference and reload persistence |

| Photo upload/preview/replace/remove | New/edit report dialog; image preview before submission; authenticated `/uploads`; attachment binding on creation/edit | API image decoding, invalid-content rejection, owner/binding/removal tests | Passed browser preview/remove/reselect, saved-photo removal/replacement and persisted evidence display |

| GPS and manual interactive map | Report dialog; browser geolocation; Leaflet point selection; coordinate inputs | API coordinate validation | Passed browser granted-GPS and map selection checks. Actual device GPS quality is external |

| Report edit | Eligible own reports only; `PATCH /reports/{id}`; bound photos checked for ownership | API edit/photo binding/date filter; assignment edit guard; stale duplicate regression | Passed browser edit/reload journey |

| Reversible withdrawal | Confirmation and Restore report; `/reports/{id}/withdraw` | API withdrawal/restore; authority active-work constraints | Passed browser withdrawal/restore journey |

| Citizen status and authority updates | Incident detail Response/Activity/Evidence; Notifications | API complete worker/verification journey and note/notification tests | Passed full browser reporting-to-resolution journey |

| Consolidated report tracking | Minimal parent reference/status shown on original report; original evidence retained | Security parent status, notification propagation and privacy tests | Authority duplicate browser controls passed; citizen consolidated projection/notifications verified in Security tests |

| Additional evidence requested after assignment | Authority requests evidence through a persisted note; Evidence tab allows citizen/official report-photo uploads on active incidents; citizen can reply with a note | Basic upload permission tests; new UI controls inspected after audit fix | Passed browser authority evidence request, assigned-citizen photograph upload and reply |



## Civic intelligence and duplicate handling



| Feature | Implementation and screen/API | Executed evidence | Limitation |

|---|---|---|---|

| Supported civic categories and safe fallback | Civic Intelligence analysis panel; rule-based text tool; `/incidents/{id}/analyze` | Intelligence supported-category/routing tests, uncertain fallback/schema tests | Default is deterministic **text** analysis. Unknown wording requires human categorization |

| Contextual severity and uncertainty | Exposure/consequence rules; Low/Medium/High/Critical; confidence null for uncalibrated rules | Intelligence contextual severity, false-confidence and image-source validation tests | Reported context is unverified; no calibrated classifier accuracy claimed |

| Department routing | Suggested configured department; authority can correct; worker assignment remains separate | Intelligence routing and API persisted department checks | Simulated organization configuration; no government service integration |

| Real vision adapter | Server-side Responses API image input and validated `HazardAnalysis` output | Intelligence mock request, output validation, bounded retry and fallback tests | **Live vision NOT verified: no provider credential configured.** Stored photos have `image_analyzed=false` in fallback |

| Duplicate candidate screening | Category + geographical radius + time window + token similarity; visible authority review | Intelligence matching factors and stale candidate tests; API duplicate relationship test | Screening score is not a duplicate probability |

| Confirm/reject/separate duplicates | Overview duplicate controls; `/incidents/{id}/duplicate`; original records preserved | API merge/reject/separate/cycle checks; Security active-work/child-workflow guards | Human reviewed relationships only; no silent deletion |

| Analysis storage/retrieval | `incidents.analysis`, agent execution output and timestamps | API reload/read checks and Intelligence pipeline persistence tests | Completed text analysis does not imply image inference occurred |



## Flooding and waterlogging intelligence



| Feature | Implementation and screen/API | Evidence | Limitation |

|---|---|---|---|

| Real weather ingestion | Open-Meteo hourly preceding/next 24-hour modeled precipitation; `/weather` | Live Lahore provider call succeeded on audit date; Intelligence complete-window/parser failure tests | Modeled rainfall, not verified local rain-gauge observations. Forecast service/network availability is external |

| Numerical zone score | Configurable weighted engine; `/risk`; normalized 0â€“100 and Low/Moderate/High | Intelligence numerical scoring, saturation, configurable weights and input validation tests; API scenario tests | Transparent heuristic; not a flood probability or official warning; no accuracy results claimed |

| Relevant unresolved hazard inputs | Geographical containment, blocked drains and water/sewer incidents; excludes closed/withdrawn/archived/merged children | Intelligence contribution/history tests and API workflow recalculation | Circular planning zones; terrain and actual drainage capacity absent |

| Historical context/provenance | Administrator-entered zone flood counts; model/settings/weather/input references saved | Intelligence provenance and missing-history checks | Seed history is clearly synthetic; authentic municipal history is not connected |

| Missing/stale data | Null complete score + Insufficient Data; missing inputs/errors retained | Intelligence missing weather/history tests; API missing scenario | A partial evidence score is not presented as a complete estimate |

| Risk map/detail panels | Disaster intelligence screen; Leaflet zone circles, hazard markers, factor/source panels and calculation time | API latest/history reads; Browser map/zone/provenance journey exists | Passed browser map/zone detail checks and final tile-loaded screenshot; tile availability remains external |

| Independent manual refresh | `/risk/refresh` can fetch weather without a new report | Intelligence weather-only change test; API clear/heavy/missing scenario tests | Passed browser acceptance |

| Scheduled refresh | FastAPI lifespan task dispatches same persisted weather/risk service at configurable interval | Scheduler tests use controlled sleep/provider and actual PostgreSQL persistence | No long wall-clock interval wait required; test provider data is not a live weather verification |

| Heavy/clear/missing demonstrations | Explicit synthetic scenario selector; `DEMO_MODE=true` and official role required | Intelligence label/restriction tests; API scenario/permissions tests | Synthetic scenarios must never be reported as observed weather |

| Immutable assessment history | Append-only scores/factors/provenance; zone-specific history API | Intelligence history preservation, Scheduler geometry preservation, API zone filter | Legacy assessments without geometry snapshots use current zone geometry as documented fallback |



## Specialist agents, authority and worker operations



| Feature | Implementation and screen/API | Backend evidence | Browser status / limitation |

|---|---|---|---|

| Three cooperating specialists | Civic â†’ numerical engine â†’ Disaster â†’ Coordinator; shared validated handoffs | Intelligence pipeline/schema/approval tests; API execution names and structured outputs | Credential-free specialists are deterministic software agents, not fabricated LLM inference |

| Tool limits, retries and errors | Bounded provider calls; allowed/used tools in execution inputs; concise decision summaries | Intelligence invalid provider retry/fallback tests; API failed-execution retry checks | Hidden chain-of-thought is not exposed. Failed retries must report failure, not success |

| Agent activity and recommendations | Agent activity Execution log/Recommendations; `/agents`, `/recommendations` | API and Security approval/rejection/override/audit checks | Passed browser approve/reject/override and execution-log inspection; approval does not dispatch or assign a team |

| Dashboard metrics/recent activity | Command centre; scoped persisted counts and recent audit events | API dashboard count consistency test | Final presentation shows the 12 original seed records; exact generated test incidents were archived reversibly after acceptance |

| Incident filters/search/detail | Incident management; text/category/status/severity/zone/date filters | API filtered lookup, inclusive-day and read persistence tests | Passed browser text/category/severity/status/zone/date filters |

| Classification/severity override | Review classification dialog; backend requires justification for changed severity | API category validation, permission and audited override tests | Re-analysis may generate a new suggestion; human correction remains in audit history |

| Notes/request updates | Response tab; note create/edit/delete; original author or admin enforcement | API note CRUD and permission tests; visible edit/delete controls now match author/admin permission | Passed browser acceptance |

| Assignment/reassignment/cancellation | Response tab; authority assigns current active team; previous assignment retained as Cancelled | API reassignment and Security historical assignment/open-organization checks | Passed browser assignment, reassignment/cancellation and refreshed state; historical records preserved |

| Worker accept/start/complete | Assigned-team records only; acknowledgement, progress, fresh completion image and notes | API full workflow and correction tests; Security fresh evidence/current assignment tests | Passed browser citizen-authority-worker-verification journey |

| Verify/reject corrections/reopen | Authority reviews evidence; Closed requires current Submitted assignment + fresh evidence; corrections require new work evidence | API complete verification/reopen/correction tests | Resolved means awaiting verification. Closed means verified |

| Archive/unarchive and retention | Confirmation; terminal incident archival; original record/evidence/audit retained | API rejection/archive/unarchive/guard tests | Soft lifecycle operations are used instead of destructive historical deletion |



## Administration, security and delivery



| Feature | Implementation and screen/API | Evidence | Limitations / remaining verification |

|---|---|---|---|

| Departments CRUD/lifecycle | Administration Departments: create/view/edit/deactivate/reactivate | API entity lifecycle; Security open-work deactivation guard | Passed browser department create/read/edit/reload/deactivate/reactivate |

| Teams CRUD/lifecycle | Administration Teams: create/view/edit/deactivate/reactivate; active department required | API entity lifecycle and invalid department; Security live-work guards | Passed browser acceptance |

| Zones CRUD/lifecycle | Administration Zones: create/view/edit/deactivate/reactivate; validated coordinates/radius/history; form maximum matches backend 50 km | API entity lifecycle/invalid radius; Scheduler historical geometry test | Passed browser acceptance |

| User CRUD/lifecycle | Administration Users: create/view/edit/disable/reactivate; self-disable/demotion protection | API role/worker-team/disabled-session/admin-self-protection tests | Passed browser acceptance; initial production admin provisioning is an explicit private command |

| Notifications read/unread | Notifications screen; strictly own records | API read/unread and Security nonowner rejection | Passed browser acceptance |

| Persistent relational database | PostgreSQL with real foreign keys/checks; separate `_test` database | Executed API/Security tests and SQL verification | Unit-only intelligence persistence tests use isolated SQLite, clearly separated from app persistence |

| Image storage and scoped reads | Durable upload directory; decoded/reencoded images; authenticated blob fetch | API invalid file, binding, ownership and retained closed-evidence checks | Deployment needs a durable volume and backup; no public bucket configured |

| Frontend build/type safety | React/TypeScript/Vite build scripts; real `/api` requests with query invalidation and errors | TypeScript and Vite production build passed; details in test report | 12 frontend unit/component tests passed, plus integrated browser journeys |

| Responsive navigation/error feedback | Desktop/mobile layout, modal forms, toast/error states and permission-aware navigation | Passed desktop/mobile and injected API-failure browser checks; final screenshots inspected with view_image | Verified at 1536×1024 desktop and 390×844 mobile; no page overflow or app runtime errors in final capture |

| Setup/start/stop and local URLs | README, environment template, Windows bootstrap and owned-process scripts | Running local services verified during implementation | Fresh-machine reproduction is separate from the prepared local environment |

| Source/SQL/docs/Desktop handoff/ZIP | Actual project source, SQL scripts, README, architecture and demo guide; source-only ZIP packager | Source inspection and ZIP integrity/secret-exclusion checks documented in final test report | Final ZIP must exclude secrets, runtime databases, uploads/dependencies and caches |

| Public deployment | Dockerfiles, nginx and Compose deployment preparation | Configuration inspection only | **Docker not executed on this machine; public deployment not performed, per user's instruction to keep the project local and push nowhere.** No public URL is claimed |



## Audit fixes and final limits



Source inspection confirms the audit fixes are present: the photo limit now matches 8 MB; Retry is restricted to Failed agent executions; note edit/delete controls follow author/admin permission; the zone form maximum is 50 km; assigned citizens have additional-evidence and reply controls; and deployment prose names `backend/app/create_admin.py`. The working provisioning command is `python -m app.create_admin` from the backend. The final 11-journey browser suite passed after these fixes, including the additional-evidence journey and auth race repair.



The three original proposal/transcript documents referenced by the pasted master prompt were not attached. The implementation uses the supplied master brief and its final integrated product direction. There is no claimed review of absent source documents.



## Preserved test evidence and presentation state



All 12 original `CS-DEMO-*` records and evidence remain. The backend suite uses a separate guarded `_test` database. After the final browser pass, 13 exact generated incident IDs were cancelled where needed, rejected/closed appropriately and archived using the application API. Generated test organizational records/accounts were deactivated; their audit trails remain. The exact-ID manifest is retained locally at `.runtime/test-record-manifest.json`; no seed reset or destructive deletion occurred.



The presentation uses a newly calculated, explicitly labeled synthetic heavy-rain scenario. This is not observed weather. Live Open-Meteo was separately verified. The source ZIP excludes the runtime database, secrets and uploads; demo fixtures regenerate on a fresh explicit demo initialization.
