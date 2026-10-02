# B19 Run A report

Date: 2026-10-02. Work was limited to the MedSafe project folder.

## Results

| Phase | Result | Pytest |
|---|---|---:|
| 0 Baseline | Captured routes, request/response fields, synthetic checker statuses and 86-file SHA inventory. | 301 passed, 1 skipped |
| 1 NOTICE | Added attribution, non-commercial and ShareAlike wording for the DDInter-derived rules and severity model. | 301 passed, 1 skipped |
| 2 Dose staging | One atorvastatin candidate staged; reviewer fields remain blank; no row promoted. Other candidates and skip reasons are in reports/b19_phase2_candidates.md. | 301 passed, 1 skipped |
| 3 Web interface | Added a no-dependency interface, static routes, CSP and /config; server and three synthetic examples returned HTTP 200. | 301 passed, 1 skipped |
| 4 LLM and packaging | Added Groq adapter, allowlisted dotenv loader, optional setup docs, archive utility, live-measurement utility and offline coverage. Strict finding-byte-identity acceptance is unresolved because accepted summaries currently live inside Finding. Live network measurement was not run. | 317 passed, 1 skipped |

No existing test assertion changed. Sixteen offline tests were added.

## What changed

Core inventory diff against Phase 0: reports/b19_run_a_hash_diff.json. Five files were added to the inventory; the listed source changes are in API, static UI, optional LLM and the two scripts. Phase 1 changed NOTICE; Phase 2 added two staged CSVs and its report. README.md, .env.example, .gitignore and reports were also updated outside the four-directory SHA inventory. Tests added: tests/test_b19_llm_config.py.

Model SHAs remain:

- severity_model.joblib: 3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c
- drug_index.json: 1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c
- manifest.json: 7921ed98394ebace748ba44207b0738d94c3a524d14b2f8be504271727216e4c

No files under models/ changed. No threshold, feature, split or training changes were made; TEST_SPLIT_TOUCH remains 0.

## Dose candidate

| Candidate | Result | Owner check |
|---|---|---|
| Atorvastatin | Staged as B19-DOSE-ATORVASTATIN-001, 80 mg once daily for the cited adult tablet label. | Open the staged DailyMed URL and verify product, strength, amount, frequency, population and product caveat. Keep both reviewer cells blank until checked. |
| Metformin | Skipped: IR and ER labels differ. | None |
| Simvastatin | Skipped: limits depend on co-medication and renal context. | None |
| Lisinopril | Skipped: limits depend on indication, renal function or age. | None |
| Digoxin | Skipped: maintenance is individualized by label factors. | None |
| Ibuprofen, acetaminophen, aspirin | Skipped: OTC product-specific labels. | None |

Full label excerpts and source links: reports/b19_phase2_candidates.md. The staged row was not promoted; DOSE remains NOT_RUN_NO_DATA.

## Phase 3 evidence

GET /, /static/app.js, /static/styles.css, /config and /health returned HTTP 200 from a local server with CSP. The three synthetic UI examples returned HTTP 200 and retained API ordering. A request-body sentinel was absent from captured logs. reports/b19_ui_manual_checklist.md holds owner visual checks. Screenshots were not taken because no headless browser was installed.

## Phase 4 evidence

Groq endpoint and request format were checked against official Groq documentation. Offline adapter and dotenv tests passed. The live script guard was checked without setting the live flag; it exited before configuration/network use. Live measurement was not run.

One acceptance issue remains: accepted AI summaries currently alter Finding.explanation.plain_language. The strict requirement for byte-identical findings conflicts with the existing UI/API summary field and the instruction to preserve the Phase 3 response schema. Run A did not add an extra report field.

## Run A boundaries

Phase 5 was not started: the only dose row still needs the owner's browser source check. Phase 6 was not started because this is Run A; it includes the final freeze, clean-copy, determinism, hygiene and archive review.

### GATE: owner steps

1. Open the staged atorvastatin DailyMed URL in reports/b19_staging/dose_limits.csv. Verify the product, strength, 80 mg amount, once-daily wording, adult population and product-specific caveat against the label.
2. If it matches, fill reviewed_by as Rithwik (source text verified; not clinical review) and verified_on as 2026-10-02 in that staged CSV. Leave mismatches blank. Do not promote it manually.
3. For a later live synthetic run only, set MEDSAFE_LLM_ENABLED=1 and MEDSAFE_LIVE_LLM_TEST=1 in the terminal. The model and provider can be set in .env; never paste the key into chat.
4. Reply continue from Phase 5 after reviewing the dose row, or skip dose, go to Phase 6 to leave dose as NOT_RUN_NO_DATA.

The finding-byte-identity issue needs an API design decision before summaries can satisfy both requirements: a separate additive SafetyReport.llm_summaries field would keep finding objects stable, but Phase 3 instructed schema preservation. Current behavior is recorded in reports/b19_phase4.md.
