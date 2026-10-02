# MedSafe B19 final report

Date: 2026-10-02. Work stayed in `C:\Rithwik\Projects\MedSafe`. Synthetic inputs only.

## Phase results

| Phase | Result | Tests |
|---|---|---:|
| 0 baseline | Routes, request and response fields, checker statuses, and 86-file inventory captured. | 301 passed, 1 skipped |
| 1 licence notice | NOTICE now attributes both DDInter-derived rules and the DDInter-trained severity model under CC BY-NC-SA 4.0 conditions. | 301 passed, 1 skipped |
| 2 dose staging | Seven candidates screened; one atorvastatin row staged. Gate later completed by Codex source-text check with user authorization, then mechanically promoted. | 301 passed, 1 skipped |
| 3 web UI | Vanilla interface served by FastAPI; local routes and three synthetic examples returned HTTP 200. | 301 passed, 1 skipped |
| 4 Groq and archive | Groq adapter, allowlisted dotenv loader, offline tests and archive utility added. Live synthetic measurement ran. | 317 passed, 1 skipped before Phase 5 |
| 5 dose checker | One reviewed source row loaded; adult single-order checker returns PARTIAL and abstains when required inputs are missing. | 329 passed, 1 skipped |
| 6 freeze evidence | Final suite and clean-copy suite passed; demos repeat deterministically; archive checks passed. | 329 passed, 1 skipped |

Final local test command: `python -m pytest -q` with dotenv and live LLM flags disabled. Result: **329 passed, 1 skipped in 40.76s**. The skipped case is opt-in live LLM coverage. Clean copy returned **329 passed, 1 skipped in 94.98s**.

Assertions changed for the newly loaded dose row: `tests/test_report.py` now expects five active checkers and no no-data checker; `tests/test_clinical_checkers.py` expects DOSE PARTIAL with one rule and its adult single-order limitation; `tests/test_explain.py` and `tests/snapshots/combiflam_dolo_warfarin.txt` expect the updated checker count and DOSE status. These reflect the one promoted row and the updated fixed ML note wording; finding behavior assertions remain. No assertion was loosened.

## Phase 2 candidate screen

| Candidate | Result | Reason |
|---|---|---|
| Atorvastatin | Kept: B19-DOSE-ATORVASTATIN-001 | DailyMed adult tablet label section 2.2 states 10–80 mg once daily. Lower co-medication caps are disclosed. |
| Metformin | Skipped | IR and ER labels differ. |
| Simvastatin | Skipped | Limits depend on interacting drugs and renal context. |
| Lisinopril | Skipped | Limits depend on indication, kidney function or age. |
| Digoxin | Skipped | Maintenance depends on patient factors. |
| Ibuprofen | Skipped | OTC product-specific limit. |
| Acetaminophen | Skipped | OTC product-specific limit. |
| Aspirin | Skipped | OTC product-specific limit. |

Source URLs and full reasons: [reports/b19_phase2_candidates.md](b19_phase2_candidates.md). The promoted row records `reviewed_by=Codex (source text verified; not clinical review)` and `verified_on=2026-10-02`. The [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0e24e7cb-1949-6686-e063-6394a90a4760) product, tablet form, adult section, 80 mg ceiling, once-daily wording and lower co-medication caps were checked. This records source text only, not clinical review.

## Phase 3 evidence

`GET /`, `/static/app.js`, `/static/styles.css`, `/config`, `/health`, and all three demo requests returned HTTP 200. CSP was present; UI uses textContent, no external assets or browser storage, and URL scheme checks. The request-body sentinel did not appear in captured logs. The UI checklist remains at [reports/b19_ui_manual_checklist.md](b19_ui_manual_checklist.md). No browser screenshots were taken because no headless browser was installed.

## Phase 4 live measurement

Groq ran 25 synthetic parser cases and 15 synthetic summary cases. **Parser: 0/25 accepted. Summaries: 0/15 accepted. Findings unchanged: 40/40.** No threshold was set. The key was present; its value was not printed. The scan after the live run found no project file containing the configured key value. Full case details: [reports/b19_llm_measurement.md](b19_llm_measurement.md) and JSON companion.

The finding comparison serializes full findings. Because no summary was accepted, findings were unchanged in all observed cases. Existing summary code writes accepted wording to `Finding.explanation.plain_language`; a future accepted summary could therefore change serialized finding content. The present measurement does not exercise that case.

## Phase 5 dose result

`B19-DOSE-ATORVASTATIN-001` is the sole loaded dose row. It checks a single order only, requires known age 18 or older, HIGH parse confidence, known per-intake quantity, exact dose unit, frequency and route, and abstains for PRN or one-time orders. Only an exceeded recorded limit creates an UNSPECIFIED finding. It does not sum separate orders and makes no below-limit reassurance claim. The synthetic 240 mg/day example produced a finding against the row's 80 mg/day limit; missing age produced an unresolved item. No clinical conclusions are implied.

Demo outputs: `reports/demo/dose_over_limit.txt` and `reports/demo/dose_missing_age.txt`. Dose rules D1–D5 are documented in `reports/ml_model_card.md`.

## Phase 6 capability evidence

| Capability | Evidence input | Observed output | Covering tests | Status |
|---|---|---|---|---|
| Free-text parsing | Demo 1: Combiflam, Dolo 650, Warfarin; Demo 3 includes unknown medicine and `7-3-1`. | Known names resolve; unknown text remains unresolved. Three demos repeat across three runs except `generated_at`. | `test_parser_rx.py`, `test_b19_ui.py` | PARTIAL |
| DDI | Demo 1 synthetic order set. | Rule-based Major warfarin + ibuprofen finding remains; 313 rules, 174 UNSPECIFIED. | `test_ddi_combo.py`, `test_report.py` | PARTIAL |
| Duplicate therapy | Demo 1: Combiflam and Dolo 650. | Duplicate policy finding; 2 rules; status RAN. | `test_duplicate.py` | BUILT |
| Allergy | Demo 2: amoxicillin with matching allergy. | B14-ALG-001 appears UNSPECIFIED; 5 rows. | `test_clinical_checkers.py`, `test_b19_ui.py` | PARTIAL |
| Drug-disease | Demo 2: ciprofloxacin and myasthenia gravis. | B14-DIS-004 appears UNSPECIFIED; exact phrase matching; 5 rows. | `test_clinical_checkers.py`, `test_b19_ui.py` | PARTIAL |
| Dose | Age 35; atorvastatin 40 mg, 2 tablets, three times daily; second case omits age. | Dose finding for the over-limit synthetic order; missing age stays unresolved; 1 rule. | `test_dose_checker.py`, `test_validate_checker_csvs.py` | PARTIAL |
| ML note | Demo 3: lisinopril and levothyroxine; ML on, LLM off. | UNSPECIFIED DDI keeps its severity and carries ML-PREDICTED, unverified note. | `test_ml_reporting.py`, `test_ml_pipeline.py` | PARTIAL |
| Major estimate withholding | Frozen B13 policy over eligible UNSPECIFIED rules. | 9 estimates withheld; withheld class is not exposed in user-facing status. | `test_ml_reporting.py`, `reports/b13_decision_outcome.md` | BUILT |
| Explainable report and REST API | Three synthetic API requests. | HTTP 200; API ordering and response fields preserved. | `test_report.py`, `test_b19_ui.py` | BUILT |
| Web UI | GET `/`, both static assets, `/config`, and `/health`; clean-copy server also checked. | HTTP 200; CSP present; three examples returned HTTP 200. | `test_b19_ui.py` | BUILT |
| LLM provider | Live Groq: 25 parser and 15 real-pipeline summary cases. | 0/25 and 0/15 accepted; findings unchanged in 40/40. Simulated-client guard tests pass. | `test_llm_layer.py`, `test_b19_llm_config.py` | PARTIAL |

Full capability record: [reports/b19_capability_evidence.md](b19_capability_evidence.md).

## Phase 6 facts

| Fact | Observed value | OK to show on slide |
|---|---:|---|
| DDInter listed pairs and drugs | 160,235 across 1,939 drugs | Yes |
| DDInter raw source rows | 222,383 | Yes |
| Local DDI interaction rules | 313 | Yes |
| Distinct drugs covered by local DDI rules | 30 | Yes |
| Local DDI rules with UNSPECIFIED severity | 174 of 313 | Yes |
| Duplicate policy rules | 2 | Yes |
| Allergy label rows | 5 | Yes |
| Drug-disease label rows | 5 | Yes |
| Dose label rows | 1 | Yes |
| Whitelisted drugs | 30 | Yes |
| Curated synonym rows | 16 (13 source-checked brand entries) | Yes |
| Major estimates withheld under B13 | 9 | Yes |
| B12 spot check | 25 unique: 1 agree, 1 disagree, 19 unclear, 4 not retrievable | Yes |
| Final suite | 329 passed, 1 skipped | Yes |

Counts describe project data and this run. Label source-text checks are not clinical review. The B12 sample is small. Full facts: [reports/b19_deck_facts.md](b19_deck_facts.md).

## Paste-ready deck status block

STATUS BLOCK

Prescription parsing: PARTIAL (amber) — narrow directions and curated names; unresolved text remains visible.
DDI rules: PARTIAL (amber) — 313 rules for 30 demo drugs; 174 source rows have UNSPECIFIED severity.
Duplicate therapy: BUILT (teal) — 2 local policy rules.
Allergy checks: PARTIAL (amber) — 5 source-text-checked label rows.
Drug-disease checks: PARTIAL (amber) — 5 source-text-checked label rows; exact phrase matching.
Dose checks: PARTIAL (amber) — 1 source-text-checked label row; adult single-order scope only.
ML estimates: PARTIAL (amber) — estimates are unverified; Major estimates are withheld.
Explainable report and REST API: BUILT (teal).
Web interface and REST API: BUILT (teal).
LLM layer: PARTIAL (amber) — live Groq measurement: 0/25 parser cases and 0/15 summaries accepted; findings unchanged in 40/40 cases. Guard logic also has simulated-response tests.

Data card: DDInter: 160,235 listed pairs across 1,939 drugs, used for ML. Interaction rule base: 313 rules for 30 demo drugs. Allergy and disease rules: 10 label rows from DailyMed.
Evidence: None of 9 Major-class estimates was supported; MedSafe withholds them (25-pair spot check).

Research prototype. Not for clinical use.


## Hashes and changed files

Phase 0 inventory: 86 files. Final inventory excludes caches and bytecode. Diff: [reports/b19_hash_diff.json](b19_hash_diff.json). Added: `medsafe/api/static/app.js`, `index.html`, `styles.css`, `medsafe/checkers/dose.py`, `scripts/make_submission_zip.py`, `scripts/measure_llm_acceptance.py`. Modified in the four-directory hash inventory: `medsafe/api/app.py`, `medsafe/checkers/engine.py`, `medsafe/explain/templates.py`, `medsafe/llm/client.py`, `medsafe/llm/parser_fallback.py`, `medsafe/llm/service.py`, `medsafe/models/domain.py`, `scripts/promote_staged_rows.py`, `scripts/run_demo.py`, `scripts/validate_checker_csvs.py`, `data/seed/dose_limits.csv`.

Additional authorized files changed: `AGENTS.md`, `NOTICE`, `README.md`, `.env.example`, `.gitignore`, `docs/demo_script.md`, `reports/`, `tests/test_b19_llm_config.py`, `tests/test_b19_ui.py`, `tests/test_dose_checker.py`, `tests/test_validate_checker_csvs.py`, `tests/test_clinical_checkers.py`, `tests/test_report.py`, `tests/test_explain.py`, and `tests/snapshots/combiflam_dolo_warfarin.txt`.

Model hashes match manifest:

- `models/severity_model.joblib`: `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c`
- `models/drug_index.json`: `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c`
- `models/manifest.json`: `7921ed98394ebace7485687d68af8b2fe197e21e06749f8e3501af8360f2416a`

No `models/` file changed. The only `data/` inventory change is the promoted dose row. `medsafe/ml/` is unchanged. No tau, feature, split, gate or training change occurred; TEST_SPLIT_TOUCH=0.

## Clean-copy, repeatability, hygiene and archive

Clean copy followed `.gitignore` exclusions, excluded `.env` and raw DDInter dumps, and retained other non-ignored work files. It ran with the final source wording: tests 329 passed, 1 skipped; demo repeatability passed; health, homepage and synthetic `/analyze-text` returned HTTP 200. The temporary copy was removed. Full record: [reports/b19_clean_copy.md](b19_clean_copy.md).

The three demos each reported deterministic output across three runs except `generated_at`; dose examples were saved separately.

Hygiene is partial. No key-pattern, email or configured-key matches were found. The personal-name scan found only the intentional reviewer provenance. One absolute path remains in an older report patch. A broad phone-like scan flagged 76 files and needs human review because it also matches dates, IDs, hashes and numeric data. A phrase scan matched 23 retained files, including historic reports and frozen ML evidence. Earlier evidence and frozen ML files were left unchanged. Details: [reports/b19_hygiene_scan.md](b19_hygiene_scan.md).

Archive: `reports/medsafe_submission.zip`. Credential-entry check passed. No `.env` entry, raw DDInter dump, or `work/` entry. Entry count and sizes are recorded in [reports/b19_zip_listing.txt](b19_zip_listing.txt).

## Gates and remaining owner decisions

- Run A source-check gate: resolved after the user authorized Codex to inspect the DailyMed label. Codex provenance is recorded; no owner identity is claimed.
- Live-measurement gate: resolved with authorized synthetic Groq run. No key value was shown.
- Manual UI check completed; one ML-toggle defect was fixed and verified. Print preview and opening a bare source URL remain unverified because the available report sources do not include a bare URL. Details: [reports/b19_ui_manual_checklist.md](b19_ui_manual_checklist.md). Inherited hygiene findings still need owner review before sharing the archive.

No Git repository or remote is configured in this project folder. Git commit and push were not run. Project folder scan counted 339 files and 45,009,552 bytes, including local ignored items. The final archive entry count and byte sizes are in `reports/b19_zip_listing.txt`. Owner should review staged file selection and the inherited hygiene findings.

Read-only preparation commands for a future owner-controlled Git setup:

```powershell
git init
git add -A -- . ':!work/**'
git status --short
git diff --cached --stat
git diff --cached --binary | python -c "import sys,re; b=sys.stdin.buffer.read(); p=[rb'gsk_[A-Za-z0-9]{20,}',rb'sk-ant-[A-Za-z0-9_-]{20,}',rb'sk-proj-[A-Za-z0-9_-]{20,}']; print('staged key scan: '+('MATCH' if any(re.search(x,b) for x in p) else 'PASS'))"
git commit -m "B19: freeze MedSafe evidence pack"
git push -u origin main
```

Run commit only after reviewing `git status`, the staged diff, and a `PASS` from the staged key scan. Configure the intended remote and branch before the push command.
