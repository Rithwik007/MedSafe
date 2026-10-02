# B19 Phase 3 — web interface evidence

The API serves the single-page UI at GET /, app.js and styles.css under /static/, plus GET /config. It reuses the analyze endpoints and keeps their finding schema as captured before Phase 3. The additive Patient field is age_years. Configuration returns only availability booleans and version.

Saved evidence:

- reports/b19_ui_server_evidence.json: live local server requests for /, both static assets, /config and /health; each returned HTTP 200. The three synthetic examples returned HTTP 200.
- reports/b19_ui_evidence.json: test-client outputs and CSP, config, logging and schema checks.
- reports/b19_ui_manual_checklist.md: responsive, keyboard, example, print, copy and link checks.

No headless browser was installed, so screenshots were not taken. The manual visual checklist remains for owner review.

Security checks recorded in the evidence: CSP on responses, static-file allowlist, textContent rendering, local-only asset references, no browser storage use, URL scheme checks, and a request-body sentinel absent from captured logs.

Phase 3 pytest: 301 passed, 1 skipped. No existing assertion changed.
