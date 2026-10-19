# Intelligence implementation and limits

CivicShield uses deterministic, inspectable decision tools in the local demonstration. No forecast accuracy, municipal validation, emergency dispatch, or government partnership is claimed.

## Report analysis

The Civic Intelligence Agent reads report text, evaluates supported hazard phrases, adjusts review priority from reported exposure and consequences, finds nearby recent candidates, and recommends a department. The fallback's `confidence` is null because its rules have no calibrated probability. Every result requires human review.

Photographs are retained as evidence. Without a server-side Gemini key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`), they are **not analyzed**. The API response explicitly includes `image_analyzed=false`, `method=deterministic_text`, and visible uncertainty text. Nothing in this fallback measures image contents.

When configured, the default Gemini integration sends the stored photo as inline Base64 image data to the Gemini `generateContent` API, using `VISION_MODEL` when set or `GEMINI_MODEL` otherwise. Select a model that supports image inputs and structured output in your account. The output is validated with the `HazardAnalysis` Pydantic schema before use. Provider errors or invalid outputs trigger the text fallback. Credentials stay on the backend. Provider output cannot call tools or write arbitrary database records.

The real network path was checked against official documentation; the request and validation behavior are covered using a controlled mock. **Live vision inference was not tested because no API credential was configured.** Configuring a credential sends incident evidence to the provider and incurs that provider's charges.

Reference: [Gemini image understanding](https://ai.google.dev/gemini-api/docs/vision).

## Duplicate candidates

Candidates must share the suggested category, be within 180 m, be within seven days, and remain unresolved and unarchived. A weighted screening score combines the category match (0.25), normalized proximity (0.35), recency (0.20), and token Jaccard similarity (0.20). Scores of at least 0.55 are suggested for authority review. These scores are **screening weights, not duplicate probabilities**. Configure `DUPLICATE_RADIUS_M` or `DUPLICATE_WINDOW_DAYS` to tune the search. Independent reports are preserved. Analysis never merges them automatically.

## Flood-risk calculation

The numerical engine calculates a normalized planning score by circular Lahore zone:

`100 × (0.42 × forecast/60 + 0.18 × recent/40 + 0.22 × drains/3 + 0.10 × water/3 + 0.08 × history/10)`

Each normalized input is capped at 1. Rainfall is in millimetres. Drain and water counts include only unresolved, unarchived, unconsolidated flood-related hazards inside the zone. Closed, resolved, rejected, withdrawn, and merged child incidents do not contribute. Electrical hazards and manholes do not contribute merely because their severity is high.

Scores below 35 are Low, 35–64.9 Moderate, and at least 65 High. Missing either rainfall window, stale weather (six hours by default), or provider failure produces `score=null` and Insufficient Data. Partial evidence remains available in factors, explicitly distinguished from a complete score. Unknown historical counts are disclosed and their term is omitted without reweighting. Zone history counts in demonstration mode are labeled synthetic / administrator-entered. Authentic municipal incident history has not been connected.

`RISK_WEIGHTS_JSON` accepts validated configuration, for example `{"forecast":0.42,"recent_rain":0.18,"blocked_drains":0.22,"water_incidents":0.10,"history":0.08,"forecast_saturation_mm":80}`. Weights must sum to 1. Other fields are `recent_saturation_mm`, `drain_saturation_count`, `water_saturation_count`, `history_saturation_count`, `moderate_threshold`, and `high_threshold`. `WEATHER_MAX_AGE_HOURS` configures freshness. These settings are transparent engineering assumptions, not fitted or validated model parameters.

Open-Meteo supplies complete preceding and next 24-hour precipitation windows using UTC hourly interval ends. Preceding rainfall is modeled data from the forecast service, **not verified local rain-gauge observations**. Every snapshot stores its source, retrieval time, interval bounds, provider grid coordinates, units, synthetic flag, and any error. Every assessment appends a record containing weather provenance, relevant incident IDs, historical source, model version, configuration, contributing points, limitations, and trigger. Existing history is preserved.

A live request for Lahore on 16 October 2026 succeeded and returned complete rainfall windows (0 mm recent, 0 mm forecast at verification time). Weather is dynamic; use the refresh control for the current result. Data attribution: [Open-Meteo](https://open-meteo.com/), [forecast API documentation](https://open-meteo.com/en/docs).

Manual refresh and the backend's `WEATHER_REFRESH_MINUTES` schedule invoke the same engine without requiring a citizen report. Incident analysis recalculates with the latest stored weather. `heavy_rain`, `clear`, and `missing` scenarios require `DEMO_MODE=true`; their source and stored provenance explicitly say **SYNTHETIC DEMONSTRATION**.

This model does not include terrain, actual drainage capacity, catchment hydrology, soil moisture, calibrated damage outcomes, or uncertainty intervals. Zone circles are planning approximations. A score is neither a disaster probability nor an official warning.

## Controlled specialist workflow

1. **Civic Intelligence Agent:** read report and optional image evidence; classify; screen duplicates; suggest department.
2. **Disaster Risk Agent:** read the computed score and provenance; inspect relevant unresolved hazards; identify reported vulnerable locations; explain missing information and propose preventive review.
3. **Response Coordinator Agent:** consume both validated handoffs; raise proposed flood-related priority when the zone score is High; produce a department, action, and justification requiring authority approval.

The local specialists are deterministic software agents with scoped tools. The civic vision tool becomes model-backed when configured. The disaster and response tools do not fabricate language-model outputs. They implement their own distinct operations and exchange validated structured results; the numerical score always comes from the engine.

Agent executions store tools allowed and used, incident/assessment references, shared inputs, validated outputs, a concise decision summary, attempts, errors, and status. These summaries are observable decisions, not hidden model reasoning. The coordinator has no dispatch or assignment tool. Recommendations remain Pending until an authorized human approves, rejects, or overrides them. Approval itself does not silently assign a team; the authority uses the assignment workflow.

## Verification

From `backend`, run `../.venv/Scripts/python -m pytest tests/test_intelligence.py -q` on Windows. The focused suite covers routing, contextual priority, honest fallback, output schema rejection, duplicate factors, numerical weather changes, incomplete weather, bounded risk, configurable weights, explicit synthetic scenarios, real-provider request construction with a mock transport, provider retries, persisted three-agent handoffs, preserved incident workflow, no automatic assignment, assessment history, and scenario restrictions. Unit persistence uses an isolated SQLite database; the running application uses PostgreSQL and is tested separately by the API integration suite.
