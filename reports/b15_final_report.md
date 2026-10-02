# B15 Final Report

## Outcome

Mechanically promoted all 10 source-text-checked rows into the allergy and drug-disease seed CSVs. Implemented exact normalized ingredient matching for allergy rows and exact case/whitespace-normalized condition matching for drug-disease rows. No disease synonyms or class-level allergy inference. The dose checker remains `NOT_RUN_NO_DATA`; no dose row was promoted. No clinical severity mapping added; clinical findings use `UNSPECIFIED` and expose the CSV label category.

The Patient model already supplied `allergies` and `diagnoses`; no model/schema changes were needed. The condition vocabulary CSV is header-only; its missing-vocabulary checks are warnings, not a prerequisite for this exact-phrase checker, so no vocabulary rows were staged.

## Promotion and validation

Promoted:
- Allergy: B14-ALG-001, B14-ALG-002, B14-ALG-003, B14-ALG-004, B14-ALG-005.
- Drug-disease: B14-DIS-001, B14-DIS-002, B14-DIS-003, B14-DIS-004, B14-DIS-005.
- Dose: none (staging file is header-only).

Not promoted: none. All staged allergy and disease rows had both reviewer fields. The promotion script refuses target rule_id collisions and header mismatches. Staged rows were left intact.

Validator output:
```text
WARNING drug_disease_rules.csv: row 2, column condition: condition not in conditions.csv
WARNING drug_disease_rules.csv: row 3, column condition: condition not in conditions.csv
WARNING drug_disease_rules.csv: row 4, column condition: condition not in conditions.csv
WARNING drug_disease_rules.csv: row 5, column condition: condition not in conditions.csv
WARNING drug_disease_rules.csv: row 6, column condition: condition not in conditions.csv
allergy_rules.csv: 5 rows
drug_disease_rules.csv: 5 rows
dose_limits.csv: 0 rows
Summary: 0 errors, 5 warnings
Exit code: 0
```
Five condition-map warnings remain because `conditions.csv` has no vocabulary rows; zero validator errors.

## Tests per part

- Before Part A: 294 passed, 1 skipped.
- After Part A promotion: 291 passed, 3 failed, 1 skipped. These were expected stale status/snapshot expectations for newly promoted rows: `test_demo_snapshot_combiflam_dolo_warfarin`, `test_checker_status_has_two_active_and_three_no_data`, and `test_overall_statement_has_required_caution_and_no_banned_phrases`.
- After Part B implementation and updated expectations: 301 passed, 1 skipped.
- Focused new checker suite: 7 passed. A test-file quoting typo caused one collection error before this run; corrected before the passing focused and full runs.
- Part C full suite: 301 passed, 1 skipped (48.98s).
- Final suite after widening the Python lint scan: 301 passed, 1 skipped (78.43s).
- No assertions weakened or removed. The final lint test scans all project Python sources except generated caches. Seven old expected-value assertions changed only because allergy and drug-disease status changed from `NOT_RUN_NO_DATA` to `PARTIAL` after review rows were promoted: four in `test_report.py` (active/no-data counts, no-data set, overall count) and three in `test_explain.py` (overall count, allergy status, disease status). Snapshot updated for the same status reason. New tests cover matching, unresolved inputs, missing patient-data wording, DDI/ML invariance, row-text lint, and banned phrases.

## Status and exact limitation wording

- Allergy: `PARTIAL`, 5 rules. `Coverage is a handful of source-text-checked label rows; this is not clinical review.`
- Drug-disease: `PARTIAL`, 5 rules. `Coverage is a handful of source-text-checked label rows; condition matching uses exact phrases only and this is not clinical review.`
- No-input additions: `No patient allergy data supplied; no exact allergy match was evaluated.` and `No patient condition data supplied; no exact drug-condition match was evaluated.`
- Unmatched inputs: `No exact reviewed allergy rule matched this allergen; this does not establish absence of a concern.` / `No exact reviewed drug-condition rule matched this condition; this does not establish absence of a concern.`
- Each clinical finding appends: `Ask a pharmacist to review this label-based finding.`
- Dose: `NOT_RUN_NO_DATA` (0 rules).
- Findings use `UNSPECIFIED` severity. The `label_category` from each row appears in the finding trigger. Evidence says `Source text verified; not clinical review`.

## Synthetic demo

Synthetic request: Combiflam, Warfarin, Amoxicillin, Ciprofloxacin; patient allergy `amoxicillin`; condition `myasthenia gravis`. It contains the expected Amoxicillin allergy and Ciprofloxacin disease finding. Existing DDI findings and ML annotations remain present. Full report: `b15_demo.txt`; first 40 lines are printed in the task result.

## Integrity

- `TEST_SPLIT_TOUCH=0`.
- `models/` hash diff is empty.
- `drug_index.json`: `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c` matches manifest.
- `severity_model.joblib`: `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` matches manifest.
- Inventory diff is saved in `b15_hash_diff.txt` and JSON.

## Exact changed files

- `AGENTS.md`
- `data/seed/allergy_rules.csv`
- `data/seed/drug_disease_rules.csv`
- `medsafe/checkers/allergy.py` (new)
- `medsafe/checkers/drug_disease.py` (new)
- `medsafe/checkers/engine.py`
- `medsafe/checkers/stubs.py` (docstring only)
- `medsafe/explain/templates.py`
- `scripts/promote_staged_rows.py` (new)
- `tests/test_clinical_checkers.py` (new)
- `tests/test_report.py`
- `tests/test_explain.py`
- `tests/snapshots/combiflam_dolo_warfarin.txt`
- `reports/b15_hash_before.json`
- `reports/b15_hash_after.json`
- `reports/b15_hash_diff.txt`
- `reports/b15_hash_diff.json`
- `reports/b15_promotion_report.txt`
- `reports/b15_validator_output.txt`
- `reports/b15_demo.txt`
- `reports/b15_final_report.md`

This folder has no Git metadata; SHA inventory proves the `medsafe/`, `models/`, and `data/` changes. No `models/` file changed.

## Not done

No dose checker, dose rows, condition vocabulary rows, severity mapping, ML changes, live LLM test, network calls, or dependency changes. Checker coverage remains a handful of rows and is not clinical review.
