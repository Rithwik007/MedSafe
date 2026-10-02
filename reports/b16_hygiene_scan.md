# B16 hygiene scan

Scope: root `README.md`, text source files under `scripts/`, and text files under `reports/`. Generated `__pycache__` bytecode was excluded. Scan looked for API-key formats, email addresses, formatted telephone numbers, personal names, and absolute Windows paths. Secret values were not printed.

## Findings

| Category | File and line | Result |
|---|---|---|
| Absolute local path and personal name | `README.md:14` | The setup example contains the machine-specific checkout path, including the account name. Remove or replace with a placeholder before submission. |
| Personal name | `reports/b14_final_report.md:7` | `reviewed_by` names the reviewer. |
| Personal name | `reports/b14_staging/allergy_rules.csv:2-6` | Reviewer field repeats the name on five rows. |
| Personal name | `reports/b14_staging/drug_disease_rules.csv:2-6` | Reviewer field repeats the name on five rows. |
| Personal name | `reports/b14_staging/review_note.txt:1` | Review note names the reviewer. |

No API-key pattern or email address found. The phone-number heuristic matched two DDInter numeric identifiers in Drugs.com URLs (`reports/b12_pass1_blind.csv:13` and `reports/ml_spotcheck_filled.csv:13`); both are URL identifiers, not telephone numbers. No verified phone number found.

## Submission implication

Hygiene scan is not clean. Existing files must remain untouched under B16's no-edit rule, so the README path and reviewer names were reported but not changed. Do not publish those files until the owner chooses how to remove or retain them.
