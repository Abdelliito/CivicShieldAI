# Civic Atlas rendered design verification

Source visual truth: `docs/redesign/atlas-workbench-concept.png` (1487 × 1058 pixels, generated visual target).

Implementation: `http://127.0.0.1:5173/`, authority role, same synthetic seed records, default unselected map, light Civic Atlas theme. CSS viewport 1440 × 1024; browser devicePixelRatio approximately 1. Source and implementation contain app content without a device frame. In-app browser capture is 1425 × 1013 pixels; both artifacts have the same aspect ratio within 0.1%. Comparison uses matched full-frame extents, not assumed pixel-for-pixel equality. Dynamic times, genuine geography, calculated risk levels and recommendation counts must remain backend truth.

## Comparison history

### Iteration 1 — blocked

Evidence: source and `docs/redesign/authority-first-render.png` opened together in one visual comparison input. Actual browser fonts and layout were also inspected: body Manrope Variable 14px, queue title 12px, compact table 11px; eight fully loaded OpenStreetMap tiles.

- **[P2] Operational typography is too small.** The implementation compresses intelligence metadata to 8px, queue references to 9px, and summary copy to 10px, below the readable scale of the reference. This impairs scanning real operational records. Increase decision-support copy to 12px, important table/queue text to 12.5–13px, metadata to at least 10.5–11px, and retain clear local font weights.
- **[P2] Major region height reduces visible ledger content.** The implementation's 382px map plus header leaves only one table row visible where the source shows three. Reduce map height toward 350px and trim vertical chrome while preserving readable fonts; keep the map as the largest visual region.
- **[P2] Focus control wraps unnecessarily.** Its icon and label form two lines. Use an inline flex row with a nonwrapping label.

Composition, palette, and source hierarchy are otherwise present: persistent forest rail, open metric rail, map/queue split, three editorial intelligence columns, incident ledger. Real OSM geography and actual circular zone extents intentionally replace inaccurate generated geography/polygons. Standard Lucide brand/navigation icons preserve a coherent icon family. No generated screenshot is used as a UI background.

## Required surfaces — initial review, superseded below

- Fonts/typography: local Manrope and IBM Plex Mono loaded. Initial small-type issues above remain blocking until revised capture.
- Spacing/layout: hierarchy matches, but vertical density finding above remains blocking.
- Colors/tokens: forest/paper/white palette and semantic critical/warning/positive states present; muted text contrasts and focus/hover states require final review.
- Images/assets: real tiles loaded, risk radii preserved, subtle dashed zones, actual evidence remains authenticated. No raster source UI substituted into code.
- Copy/content: source's invented timestamps, maps and pending states replaced with actual persisted data. Text rules, weighted risk, rule-based coordinator and required human decisions remain explicit.

## Implementation checklist

1. [x] Apply typography, spacing and focus-control fixes.
2. [x] Capture revised full viewport and focused regions; compare with the source in the same input.
3. [x] Inspect mobile/tablet and all four role routes.
4. [x] Execute workflow and responsive/map regressions; resolve failures.

## Iteration 2 — metadata refinement

Compared `authority-revised-render.png` with the source in the same input. Increased queue/table/body type fixed the legibility finding, and Focus Lahore became one nonwrapping control. A remaining P2 was the full method/timestamp span wrapping beside the execution badge and making intelligence columns unnecessarily tall. Split factual method/status and timestamp/review state into separate rows, set summary line-height to 1.6, and tighten column/header spacing. Keep full methods available in the detailed records.

## Iteration 3 — final comparison

Final implementation evidence: `docs/redesign/authority-final-1440.png`, 1425 × 1013 capture pixels at CSS 1440 × 1024 and DPR approximately 1. The source remains 1487 × 1058. Both were normalized to **1440 × 1024**, with negligible aspect correction below 0.1%, and opened together in the same comparison input:

- Full view: `docs/redesign/source-normalized.png` and `docs/redesign/render-normalized.png`.
- Focused intelligence/ledger region: `docs/redesign/source-intelligence-ledger.png` and `docs/redesign/render-intelligence-ledger.png`, each **1200 × 384**, cropped from the same normalized rectangle `(240,640)–(1440,1024)`. Both crops were inspected together; readable metadata, badges, separators, and table alignment were reviewed directly.

The earlier P2 findings are resolved. The final map/queue split, open metric rail, three distinct specialist columns and ledger follow the selected composition. Actual summaries, execution status and pending-review counts replace the source's invented timestamps/approval labels. The ledger begins roughly 27px lower than the normalized image because the implementation retains legible factual metadata and real summary wrapping; this is an accepted product/content tradeoff. The visible first rows and full five-row ledger remain immediately accessible through normal scrolling. It does not hide a control or create a broken region.

| Fidelity surface | Final assessment |
|---|---|
| Fonts and typography | Locally loaded Manrope Variable and IBM Plex Mono confirmed in the browser. Queue title13px, compact ledger12.5px, intelligence body12px and mono metadata10.5px. Clear heading/body/meta hierarchy and consistent weights; actual content wraps without collision. |
| Spacing and layout | Compact command header, unified summary, dominant map, divided queue and editorial intelligence restored. Responsive structures and scroll containers remain contained. No actionable P0/P1/P2 layout findings remain. |
| Color and tokens | Paper `#F5F3EE`, forest `#202A29`/`#285E51`, white surfaces and semantic critical/warning/positive treatments follow the brief. Darker label colors accompany amber fills. Focus, selected, hover, error and disabled states remain visible. No formal whole-product WCAG certification is claimed. |
| Images and assets | Final browser read confirmed **15 loaded OSM tiles**. Real geographic positions and stored circular radii intentionally supersede inaccurate generated roads/polygons. Zones use subtle dashed outlines and0.045fill opacity. Standard Lucide icons remain consistent; no flattened UI image or decorative substitute artwork is used. |
| Copy and content | The current role, synthetic provenance, source timestamps, specialist methods and human decision states are explicit. Successful rule execution does not claim live image understanding or automatically approved work. |

## Responsive and interaction evidence

All four roles were exercised at1440,1280,768 and390px. Screenshots are in `docs/redesign/qa/`; mobile reporting, location/camera controls, selected-map context, authority drawer, specialist activity and Administration also have direct in-app browser captures in `docs/redesign/`.

Actual fixes from these checks: mobile close control and inert/focus handling; a table's visually hidden absolute heading escaping its scroll context (fixed with positioned table scroll containers, rather than hiding page overflow); map zoom/recenter race; SVG/HTML opener focus recovery; coordinate-empty validation; rejected-photo preview preservation; stale selected records. The 390px document and body both measure390px while the730px incident table scrolls within its own356px viewport.

Executed acceptance: **32 unique browser checks passed after fixes and focused reruns**, with **70 backend tests** and **12 frontend tests** passed. The browser suite checks actual authenticated API reads, authorized routes, no local app-script errors, no page exceptions, layout, photo/camera chooser, map layers, keyboard selection, risk factors/history and dialog focus. See `docs/redesign/browser-verification-summary.json` for the latest executed result of every browser check. One combined run's artifact collision was corrected with isolated output folders; no test was skipped.

Remaining external verification limits: physical phone camera/GPS hardware, credentialed live vision, and container/public deployment. These are not presented as verified by screenshots or mocked provider responses.

final result: passed
