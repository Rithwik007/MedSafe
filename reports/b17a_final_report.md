# B17a final report

## Outcome

B17a completed as a staging-only assessment. No rows qualified, so both staging CSVs contain headers only. Nothing was promoted. B17b was not run. Reviewer fields were not populated: B17a explicitly forbids self-review, and there were no rows to review.

## 1. Hash and tests

- SHA-256 inventory covers `medsafe/`, `models/`, and `data/`. Diff: empty (`reports/b17a_hash_diff.txt` is `{}`).
- Pytest before: **301 passed, 1 skipped**.
- Pytest after: **301 passed, 1 skipped** in 85.70s.
- `TEST_SPLIT_TOUCH 0`: no model or split files were changed; inventory diff is empty.

## 2. Part A

See `reports/b17a_part_a.md` for the exact CSV header, validator rules, parser field meanings, patient age field, and Dolo 650 alias/strength handling.

## 3. Staging files (full contents)

`reports/b17_staging/dose_limits.csv`:

```csv
rule_id,drug,route,population,age_min_years,age_max_years,dose_unit,max_single_dose,max_daily_dose,per_kg_basis,renal_note,source_name,source_url,source_section,accessed_on,reviewed_by,verified_on
```

`reports/b17_staging/excerpts.csv`:

```csv
rule_id,source_excerpt
```

## 4. Candidate dispositions

All eight prompt hints were considered and skipped: acetaminophen and ibuprofen provide tablet/caplet-count directions requiring a prohibited strength conversion; metformin has indication/titration/renal qualifications and no explicit matching single-dose limit; atorvastatin lacks an explicit single-dose limit and has context-dependent dosing; simvastatin limits vary with indication/interacting therapy; aspirin requires converting tablet counts; lisinopril dosing is indication/titration dependent; digoxin dosing is individualized. The exact per-candidate table is in `reports/b17a_candidates.md`.

No staged rows means the row-by-row browser verification addendum did not apply. No excerpts were created, and no reviewer identity/date was set.

## 5. Temporary-copy validator output

The validator ran against a temporary copy of `data/` with the header-only staged file appended. The temporary directory was removed afterward.

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
```

The validator reports 0 errors and 5 warnings. All five are existing `drug_disease_rules.csv` condition warnings, not dose-row errors. There are no blank-age errors because no dose rows were staged.

## 6. Scope limits

No clinical verification is claimed. No project code, model, or data files were edited. No dependency, API, network-calling code, or LLM call was added or used. The validator was not amended to resolve its current population/age-schema conflict; B17a prohibits code edits.
