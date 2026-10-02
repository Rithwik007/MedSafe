# B14 Final Report — staged clinical rows only

Date: 2026-10-02

## Outcome

Staged five allergy rows and five drug-disease rows using DailyMed label text fetched for this task. Dose staging is header-only: the sourced adult dose labels do not state a finite maximum age, while the existing dose validator requires numeric minimum and maximum ages. Assigning an upper age would be unsupported. Per the user instruction, `reviewed_by=Rithwik` and `verified_on=2026-10-02` are recorded on all ten staged rows. The review note says: source text verified; not clinical review. These rows are not clinically verified and do not activate checks: the three implementations remain stubs.

## Integrity and tests

- Before/after inventory: 104 files each under `medsafe/`, `models/`, `data/`.
- Hash diff: empty (0 added, 0 removed, 0 changed). See `b14_hash_diff.txt`, `b14_hash_before.json`, `b14_hash_after.json`.
- Tests before staging: 294 passed, 1 skipped.
- Tests after staging: 294 passed, 1 skipped.
- Tests after source-check corrections: 294 passed, 1 skipped (84.64s).
- `TEST_SPLIT_TOUCH=0`; no model or ML files changed.
- No assertions changed; no project code/data files were edited. No live LLM/API call.

## Validator on temporary copy

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

All five warnings are due to the project’s currently empty `conditions.csv`; the validator reports these as warnings in non-strict mode. The staged reviewer fields are populated as requested; validator reports no review-field errors. No source CSV under `data/` was changed; validation appended rows only in a temporary repo copy, deleted automatically after the run.

## Source-text verification by user request

All ten excerpts were checked against their cited DailyMed sections. Eight matched as written. Two mismatches were corrected: the linked ciprofloxacin page says "Ciprofloxacin is contraindicated" (not "Ciprofloxacin tablets are contraindicated"); the linked ibuprofen page says "contraindicated in the setting of CABG surgery" and does not say "perioperative pain." Staged wording now matches the cited labels. This records source-text verification, not clinical review.

## Next steps

Do not promote yet. Checker logic remains unimplemented. Promotion requires a separate task. The dose schema's finite maximum-age requirement needs a design decision before dose rows can be represented without inventing ages.

## Detailed evidence

- Part A schema and engine inputs: `b14_part_a.md`.
- Candidate disposition: `b14_candidates.md`.
- Full validator stdout: `b14_validator_output.txt`.
- Staged CSVs and verbatim excerpts: `b14_staging/`.
