# Architecture and implementation boundaries

The browser uses same-origin `/api` requests through Vite locally or nginx in a container. FastAPI validates requests with Pydantic, authenticates signed expiring JWTs, checks role and record scope, and writes through SQLAlchemy to PostgreSQL. Authenticated attachment endpoints serve images stored on disk; completion evidence and report evidence share metadata with distinct kinds. No operational records live only in React state.

## Integrated lifecycle

Citizen report creation persists an incident and original report record. The backend runs Civic Intelligence, recalculates risk from current evidence, passes the numerical output to Disaster Risk, and gives both outputs to Response Coordinator. Structured execution records and recommendations persist. Analysis cannot assign teams. An authority approves a recommendation and separately assigns a team. Workers acknowledge, start work and submit notes plus completion evidence. An authority reviews evidence and closes or requests corrections. Status events create audit entries and citizen notifications.

Persisted incident states: Submitted, Under Analysis, Pending Review, Assigned, In Progress, Resolved, Closed, Rejected, Withdrawn, Reopened. Resolved means work is awaiting authority verification. Closed means verified. Withdrawal is reversible; archival and deactivation preserve history. Duplicate matching never deletes original submissions. Confirmed merges preserve the relationship and can be separated.

## Roles

| Role | Record access and actions |
|---|---|
| Citizen | Own reports and evidence; permitted edit, withdraw/restore, own notifications |
| Worker | Incidents assigned to own active team; acknowledgement, work and evidence |
| Authority | Review/edit incidents, justified severity decisions, duplicates, notes, assignments, verification, risk and recommendations |
| Administrator | Authority capabilities plus departments, teams, users, zones and configuration |

JWT signing secrets and provider credentials stay on the server. Disabled accounts lose access even with a previously issued token. File content is decoded and validated as an image rather than trusting an extension. Upload access requires ownership or incident access.

## Three cooperating agents

1. Civic Intelligence receives report text, photo metadata and local context. It validates classification and severity, routes to a configured department and records duplicate candidates using proximity, category, time and token similarity. The optional vision tool sends the actual photo to the configured provider and validates its JSON output. Fallback explicitly records that image understanding did not run.
2. Disaster Risk reads only calculated risk and relevant zone hazards. It explains factors and missing evidence. It cannot supply a score independent of the numerical engine.
3. Response Coordinator reads both validated outputs and the incident context, prioritizes preventive actions and persists a pending recommendation. Approval is a human API operation. Recommendation approval does not dispatch a team.

Tool capabilities, inputs, structured outputs, summaries, errors and attempts are logged. Provider operations have bounded retries. The normal credential-free mode runs rule-based specialist agents; it is not advertised as language-model inference. Internal chain-of-thought is never requested or displayed.

## Risk estimate

The default normalized weighted score combines next-24-hour modeled rain (42%), preceding-24-hour modeled rain (18%), unresolved blocked drains (22%), water/sewer incidents (10%) and administrator-entered historical flood count (8%). Inputs are capped and normalized by configurable thresholds. `RISK_WEIGHTS_JSON` can override validated weights. Risk categories are Low, Moderate, High and Insufficient Data. See the actual implementation in `backend/app/intelligence.py` for thresholds and factors stored on each assessment.

Missing or stale rain produces Insufficient Data rather than a misleading complete estimate. Every assessment stores a timestamp, weather snapshot reference, source, synthetic flag, incident IDs, history source, component values and weights. Zone circles approximate planning areas; terrain, drainage capacity and hydrology are not modeled. This model has no claimed forecast accuracy.

Risk recalculation runs on report/workflow changes, authority refresh and scheduled weather refresh. A weather change can change risk without a new report. History is preserved.

## Operational preparation

Separate source, configuration, database data and uploads. Docker Compose includes durable database/upload volumes and service readiness. Back up PostgreSQL and uploads together. Production needs HTTPS, restricted origins, non-demo accounts, private storage, tested backups, monitored logs and provider credentials if desired. No public host was configured or contacted for publication.
