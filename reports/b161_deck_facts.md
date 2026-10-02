# B16.1 deck facts (reconciled)

All rows below are counts. These values describe repository artifacts or the small source spot check; they are not clinical validation or model accuracy claims.

| Fact | Value | Source / method | OK to show on slide? |
|---|---:|---|---|
| DDI rules loaded | 313 | `data/seed/rules.csv` data rows | Yes |
| Distinct drugs covered by DDI rules | 30 | Distinct names across the `drugs` fields | Yes |
| DDI rules with `UNSPECIFIED` severity | 174 | Severity count in `data/seed/rules.csv` | Yes |
| Duplicate-policy rows | 2 | `data/seed/duplicate_policy.csv` data rows | Yes |
| Allergy rows | 5 | `data/seed/allergy_rules.csv` data rows | Yes |
| Drug-disease rows | 5 | `data/seed/drug_disease_rules.csv` data rows | Yes |
| Dose rows | 0 | `data/seed/dose_limits.csv` has header only | Yes |
| Demo whitelist drugs | 30 | 30 lines in headerless `data/seed/drug_whitelist.csv` | Yes |
| Verified brand-to-ingredient mappings | 13 | Verified synonym rows with nonempty ingredient field | Yes |
| DDInter total unique pairs | 160,235 | `reports/ml_data_audit.md`, canonicalized | Yes |
| DDInter unique drugs | 1,939 | `reports/ml_data_audit.md` | Yes |
| DDInter Unknown-severity pairs | 29,813 | `reports/ml_data_audit.md`, deduplicated | Yes |
| Tests | 301 passed, 1 skipped | Final `python -B -m pytest -q` | Yes |
| Major estimates withheld on `UNSPECIFIED` rules | 9 | `reports/b13_exposure.md` | Yes |
| B12 pairs checked | 25 | Reconciled unique pairs | Yes |
| B12 agree | 1 | Filled source-review sheet | Yes |
| B12 disagree | 1 | Filled source-review sheet | Yes |
| B12 unclear, excluding not retrievable | 19 | Filled source-review sheet, exclusive categories | Yes |
| B12 not retrievable | 4 | `source_result=not_retrievable`, exclusive categories | Yes |
| B12 Major pairs with definite answer | 0 of 9 | None had `agree` or `disagree` | Yes |

Do not state these counts as accuracy or clinical performance. The B12 result is a small spot check only.
