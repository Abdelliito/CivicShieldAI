# API reference

Interactive, generated API documentation is served by FastAPI at http://127.0.0.1:8000/docs and the machine-readable schema at http://127.0.0.1:8000/openapi.json. All application endpoints use `/api`.

Sign in with JSON `{email,password}` at `/api/auth/login`. Pass the returned token in `Authorization: Bearer <token>` for subsequent requests. Registration accepts only citizen profile fields. Role and record-scope checks run in the backend.

The full shared route/field contract is in `CONTRACT.md`. Actual request validation and allowed status transitions are defined in `backend/app/schemas.py` and `backend/app/main.py`. Validation returns 422, unauthorized access 401, forbidden actions 403, unknown or inaccessible records 404, and invalid lifecycle/resource conflicts 409. The frontend displays these errors.

Important lifecycle distinctions:

- POST `/reports` creates both original report and incident, then runs analysis.
- PATCH `/reports/{id}` edits a citizen's eligible report. Evidence is uploaded using multipart `/uploads`; new attachment IDs can be bound during creation/edit.
- POST `/incidents/{id}/assignments` is a human authority action. Reassignment preserves cancelled assignment history.
- PATCH `/assignments/{id}` supports acknowledgement/start/submission, subject to team ownership and current-assignment checks.
- Workers must upload fresh completion evidence and notes before submission. Only authorities verify closure.
- POST `/incidents/{id}/status` follows the transition graph, rejects shortcuts and records reasons/history.
- Duplicate merge/separate operations preserve original citizen data. Citizens receive only permitted consolidated incident status.
- DELETE organizational entities means deactivation; history is retained. Referenced active work may prevent deactivation until reassigned.
- Agent recommendations are proposals. Approval is audited and does not silently create work assignments.
- Risk refresh accepts synthetic scenarios only with demo mode enabled and authority permissions.

Read-only history endpoints preserve risk assessments, agent executions and audit events. Images require authenticated scoped requests; the frontend obtains blobs rather than placing bearer tokens in URLs.
