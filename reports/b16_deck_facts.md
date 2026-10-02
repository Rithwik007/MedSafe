# B16 deck facts

Counts below come from local project files. A count is not a clinical validation result.

| Fact | Value | Source and count method | OK to show on a slide? |
|---|---:|---|---|
| DDI rules loaded | 313 | `data/seed/rules.csv`; count data rows loaded by `medsafe/kb/rules.py`. | Yes |
| Distinct drugs covered by DDI rules | 30 | `data/seed/rules.csv`; split each DDI `drugs` field and count distinct names. | Yes |
| DDI rules with `UNSPECIFIED` severity | 174 | `data/seed/rules.csv`; count DDI rows with severity `UNSPECIFIED`. | Yes |
| Duplicate-policy rows | 2 | `data/seed/duplicate_policy.csv`; count data rows. | Yes |
| Allergy rows | 5 | `data/seed/allergy_rules.csv`; count reviewed data rows loaded. | Yes |
| Drug-disease rows | 5 | `data/seed/drug_disease_rules.csv`; count reviewed data rows loaded. | Yes |
| Dose rows | 0 | `data/seed/dose_limits.csv`; header-only, zero data rows. | Yes |
| Demo drug whitelist | 30 | `data/seed/drug_whitelist.csv`; one header plus 30 entries (the header is the first drug name). | Yes |
| Verified brand-to-ingredient mappings | 13 | `data/seed/synonyms.csv`; count rows with `verified=yes` and nonempty `ingredients`; 16 rows total, 3 unresolved brand-family rows. | Yes |
| DDInter total unique pairs | 160,235 | `reports/ml_data_audit.md`; local DDInter audit, canonicalized pairs, highest severity retained. | Yes |
| DDInter unique drugs | 1,939 | `reports/ml_data_audit.md`; unique canonical drug names. | Yes |
| DDInter Unknown-severity pairs | 29,813 | `reports/ml_data_audit.md`; deduplicated unique pairs labeled Unknown. | Yes |
| Tests | 301 passed, 1 skipped | `python -B -m pytest -q`; B16 baseline and Part A post-run. | Yes |
| ML Unknown-severity pairs | 29,813 | `reports/ml_unknown_distribution.md`; overall DDInter Unknown-pair denominator. | Yes |
| Major estimates withheld on UNSPECIFIED rules | 9 | `reports/b13_exposure.md`; re-scored 174 unspecified rules with frozen model/tau. | Yes |
| B12 spot-check tally rows | 29 recorded | `reports/b13_decision_outcome.md`; tally categories sum to 29. The underlying `reports/b12_pass1_blind.csv` has only 25 rows, so this count is inconsistent and must be reconciled. | Yes, only with discrepancy stated |
| B12 definite agree | 1 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |
| B12 definite disagree | 1 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |
| B12 unclear | 23 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |
| B12 not retrievable | 4 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |

## Limits for slides

The B12 tally has a source-row mismatch: its recorded categories total 29, while the blind CSV contains 25 rows. Treat its counts as unreconciled. The report also says 0 of 9 Major model outputs had a definite outside-source answer. Major ML notes remain suppressed. The spot check is small and does not establish model performance.

Do not claim the prototype checks all 160,235 DDInter pairs. It loads 313 DDI rules for the 30-drug whitelist, and the model can make unverified estimates beyond those rules.
