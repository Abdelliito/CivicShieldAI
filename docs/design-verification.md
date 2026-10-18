# Interface specification and visual verification

The Frontend App Builder and ImageGen skills produced the full command-centre reference at `docs/design-concept.png`. The built-in ImageGen tool generated the reference; it is a design artifact, never a screenshot masquerading as a working interface.

## Concept brief and design system

The generation prompt requested a complete 1536 × 1024 CivicShield AI desktop command centre for Lahore, with the exact tagline “Predict Risks. Prevent Disasters.” It specified a navy sidebar, restrained cyan accents, four metrics, a large interactive city map, priority queue, recent incident table and three agent summaries. Navigation: Overview, Incidents, Disaster intelligence, Agent activity, Administration and Notifications. It explicitly required synthetic data labeling, real implementation later, no invented civic partnerships, no forecast probabilities and no decorative photographs.

Implementation tokens: background `#0a1120`, sidebar `#0e192b`, panel `#101d30`, border `#20324a`, accent `#3bdecd`; white text with blue-gray secondary labels, amber warnings and coral critical hazards. Inter/Segoe UI sans-serif, deliberate typography on controls, consistent Lucide outline icons. Component families: app shell, route header, four metric panels, Leaflet map, priority rows, incident table, status badges, accessible Radix dialogs, forms, activity timelines and scoped administration tables. The map is code-native and interactive. No generated imagery is used as functional UI. No color overlays or raster product assets are needed.

The same component families extend into citizen reporting, worker assignments, risk details, notifications and administration. The citizen's New report control is primary; the authority's refresh and review actions are primary in its workspace. Mobile uses a drawer navigation, stacked map/queue, two-column metrics and contained horizontal table scrolling.

## Verification method

The standalone Browser skill was not listed. Repeatable acceptance and viewport screenshots use installed Playwright Chromium, as allowed by the Frontend Testing Debugging fallback. The app was also opened in the Codex in-app browser, signed into the Authority workspace, and its visible command centre checked. The browser tab is retained as a deliverable.

Reference and rendered desktop/mobile screenshots were inspected directly with `view_image`. Desktop viewport: 1536 × 1024; mobile: 390 × 844. Full-page screenshots preserve content below the viewport. Tests check page identity, meaningful headings, absence of runtime exceptions, responsive overflow and a real API failure state. Final screenshots are `docs/verified-command-centre.png` and `docs/verified-mobile.png`.

## Fidelity and repair ledger

| Comparison | Reference / render evidence | Repair or intentional extension |
|---|---|---|
| Main composition | Navy sidebar, four metrics, map left and priority queue right, table and agent activity below | Preserved as reusable layout; mobile stacks panels without covering main content |
| Palette and framing | Flat navy surfaces, thin blue-gray borders, restrained cyan, amber and coral | Implemented named tokens; no added glows or decorative image overlays |
| Typography and controls | Clear heading hierarchy, readable labels, compact tables and outline icons | Raised small captions/table controls; labels linked to inputs with separate accessible hints |
| Map imagery and geography | Reference illustrates city roads and circular risk areas | Replaced a tile service requiring a key with actual OpenStreetMap tiles and a dark presentation filter; external tile loading verified |
| Copy and role controls | Concept includes illustrative counts/status wording and an authority New report button | Real persisted metrics and consistent lifecycle labels replace examples. New report appears for citizens; Administration appears for administrators |
| Timestamp and activity evidence | Concept has relative dates and three different specialist summaries | Fixed explicit UTC-offset parsing; dashboard selects latest distinct agent summaries |
| Feedback and responsive behavior | Working control-room hierarchy and usable forms | Fixed notification overlays intercepting table actions and mobile sidebar remaining on screen; toast close control remains interactive |
| Decision details | Required explainability and source disclosure | Human-readable summaries plus optional expandable structured evidence; synthetic sources and unprocessed images explicitly identified |

Above-the-fold copy was compared against the concept and supplied product brief. Intentional additions are operational context (“Civic operations”, “Current records”), persisted new/unresolved/high-critical subcounts, role-specific names, and source-disclosure text needed for actual functionality. Concept sample counts, references and geographic illustration are replaced by database records and real map geography. These differences are documented rather than presented as pixel-identical text.

The implementation was visually verified against the accepted generated design system and composition with these functional extensions. The local screenshot shows a working React/FastAPI/PostgreSQL application. It does not establish external forecast accuracy, live vision access or a public deployment.
