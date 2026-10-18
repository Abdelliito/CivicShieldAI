# Civic Atlas redesign

## Audit evidence and decision

Inspected the actual authority dashboard, incident detail, and citizen reporting form in the in-app browser before implementation. Baseline screenshots: `before-authority.png`, `before-incident.png`, `before-citizen-report.png`. Existing behavior remains the integration contract.

The old composition repeated four isolated metric cards and similarly weighted panels. Dense navy surfaces reduced table readability, queue rows lacked an explicit next step, and saturated risk overlays obscured streets. Mobile reporting requires readable input labels, usable photograph controls, and a map that does not compete with the form.

Two distinct image concepts were produced against the real baseline:

- **Atlas Workbench** (`atlas-workbench-concept.png`): persistent forest navigation, single open summary rail, map as the operational anchor, divided priority queue, three editorial intelligence columns, full-width incident ledger.
- **Operations Ledger** (`operations-ledger-concept.png`): horizontal navigation, separate area rail, central queue, map on the right, compressed agent ribbon.

Selected Atlas Workbench. It keeps navigation predictable across four roles, gives the map more usable space, and clearly distinguishes specialist responsibilities. The alternate area's extra rail and top navigation consume useful working space. Selection is within the user's request to compare and implement the stronger direction.

## Visual contract

| Token | Value / use |
|---|---|
| Canvas | `#F5F3EE` |
| Surface | `#FFFFFF` |
| Navigation / ink | `#202A29` |
| Muted | `#6D7772`; darken where necessary on cream |
| Primary | `#285E51` |
| Warning | `#D49A43`, with darker text for readable labels |
| Critical | `#B94A43` |
| Positive | `#34765D` |
| Border | `#E5E7E2` |
| Interface font | Manrope, locally packaged variable font |
| Metadata font | IBM Plex Mono, locally packaged |

Use thin separators and whitespace to structure related content. Use cards for contained records and decisions, not as the only layout primitive. Place actual data recency and source context near operational decisions. Severity, workflow status, and recommendation approval have different labels and meanings.

## Interaction and data contract

- Keep authenticated API queries, role gating, mutation hooks, persistence, audit history, and accessible dialog handling intact.
- Authority/admin see their complete operational picture; citizens see their own reports; workers see assigned work. Only citizens can create reports.
- Map markers and risk circles use real API records. Risk circle radii retain stored geography, with subtle transparent fill and dashed borders. Tile cartography uses OpenStreetMap attribution.
- Incident and flood-risk switches work independently. Severity filtering affects markers. Focus Lahore restores the full operational extent. Markers support Enter/Space, expose selected state, and connect to a context panel and the existing detail dialog.
- All timestamps and summary numbers come from query state or persisted data. Generated concept copy, geography, and suggested times are visual references only.
- Civic Intelligence uses configured vision when available and transparent text rules otherwise; Disaster Risk uses the weighted engine; Response Coordinator proposes actions for authority review. Do not present deterministic components as three connected language models.
- Synthetic demonstration data and weather provenance remain visible.

## Verification targets

Desktop at 1440 and 1280px, tablet at 768px, mobile at 390px. Check every authorized route for all four roles, keyboard navigation, photograph/location controls, map interactions, dialog focus restoration, and whole-page overflow. Run existing workflow regressions and unit/API tests; inspect rendered screenshots and compare the selected source with the implemented screen in the same visual review.
