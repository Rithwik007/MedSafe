# B19 UI manual check results — 2026-10-02

Checked the FastAPI UI in the in-app browser at 1280×900 and 390×844. Used only the three built-in synthetic examples and a synthetic invalid-input string. No patient data was entered.

## Results

- **Responsive layout — PASS.** At 1280 px, input and report panels render in two columns. At 390 px, panels stack in one column. The document width is 375 px, so no horizontal overflow occurs in the 390 px viewport. The research-prototype warning remains visible.
- **Keyboard focus — PASS.** Tab from the prescription input moves focus to the next field. The focused textarea shows a solid outline approximately 2.3 px wide.
- **Synthetic examples — PASS.** All three buttons load their documented fields. Example 1 and 3 leave optional patient fields blank; Example 2 loads allergy and diagnosis values. Analyze returns a report for each.
- **Severity and checker wording — PASS.** Report output shows severity counts and checker statuses with the API's ordering and wording.
- **Source rendering — PARTIAL.** Source strings containing identifiers or filenames remain plain text, as intended. This run found no bare HTTP(S) source link, so opening a source in a separate tab could not be checked.
- **ML estimate toggle — PASS after fix.** The checkbox rerenders the existing report. Turning estimates off removes only the estimate block; turning them back on restores it. Finding text, severity counts, checker statuses, unresolved items, and disclaimer stay unchanged.
- **AI summary control — PASS.** `/config` reports LLM unavailable; the AI-worded-summary control remains disabled.
- **Input validation — PASS.** Empty prescription shows “Enter at least one prescription order before analyzing.” Age 121 shows “Age must be a whole number from 0 to 120.” The client validates both before its analyze fetch.
- **Copy — PASS.** Copy placed report text on the clipboard and showed its confirmation message.
- **Print — NOT VERIFIED.** Print was enabled. Clicking it opened the browser's print flow and the automation call timed out. The page's print stylesheet exists. No print preview was captured.
- **Clear — PASS.** Clear empties all fields, restores the ML checkbox, disables Copy and Print, and clears the report.
- **CSP and external requests — PASS.** The page returned HTTP 200 with `default-src 'self'`, `script-src 'self'`, `style-src 'self'`, and `connect-src 'self'`. The page loaded only local CSS and JavaScript assets. Browser console had no warnings or errors.

## Follow-up

Verify Print preview and a bare source URL when such a source is available.
