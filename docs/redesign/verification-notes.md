# Civic Atlas integration notes

The redesign preserves the role-specific routes, authenticated client, React Query invalidation, real API mutations, PostgreSQL persistence, evidence storage and existing report lifecycle. Authority and Admin can inspect incidents, risk and agent activity; Administration appears for Admin. Citizen reporting and phone-camera capture appear in the Citizen workspace. Worker tasks retain progress, evidence submission and authority verification.

## Implemented corrections found during review

- UTC date-only incident query bounds no longer inherit PostgreSQL's Asia/Karachi session timezone. Explicit offsets remain valid. The full backend suite now has 70 passing tests, including a deterministic timezone-boundary regression.
- Map selection stores an incident ID and derives current details after refetch; risk details follow the current selected zone assessment.
- Map extents update only when geographical bounds change; routine record refetch does not reset a user's map view. Explicit Focus Lahore restores the extent. Zoom animation is disabled to avoid a mid-animation recenter race.
- Incident markers and risk circles support keyboard activation. Dialogs explicitly restore focus to HTML or SVG openers, including React Strict Mode. Nested dialogs retain their own focus handling.
- Mobile navigation hides inactive links from keyboard access, supports Escape/focus trapping and includes a visible close control.
- Table scroll containers establish their own positioning context. A visually hidden absolute table heading had escaped its scroll container and caused 705px document overflow on 390px screens; the corrected document is 390px while the table retains its own 730px horizontal scroll area.
- Route changes start at the page heading; dialog/tab changes preserve the current view.
- Coordinate drafts remain strings while editing. Clearing a required coordinate stays empty and invalid instead of silently changing it to zero. Only valid coordinates recenter the picker.
- Oversized/invalid replacement photographs leave the prior preview intact. Preview URLs are cleaned up on replacement/unmount and removal resets file inputs.
- The camera action requests the rear camera through `capture="environment"` on supported phones. A separate ordinary photograph picker remains available. Browser tests exercise the capture attribute, camera/file chooser and actual preview; physical phone camera hardware is outside this Windows browser verification.
- Completion notes require ten trimmed characters before any upload, consistent with the backend guard.

## Honest intelligence status

Civic Intelligence uses transparent report-text rules by default, Disaster Risk uses the numerical weighted engine, and Response Coordinator uses validated rules/handoffs. All three persist executions and cooperate in the reporting workflow. A configured server-side vision adapter can analyze photographs, but no successful credentialed live vision call has been verified in this environment. These three specialist components must not be described as three connected language models.

## Design integration

MagicPath required external login, so work continued locally with Product Design and the connected Figma integration. Four editable Figma screens and shared tokens/components were built. The running frontend uses source components and actual map tiles, not flattened screenshots. Local Manrope and IBM Plex Mono assets avoid a third-party font request.
