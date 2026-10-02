# B16.1 final report

## 1. Integrity and tests

- Cache-excluded SHA-256 inventory covers `medsafe/`, `models/`, `data/`, and `scripts/`: **83 files**. Diff is empty; see `reports/b161_hash_diff.txt`.
- Pytest before: **301 passed, 1 skipped**.
- Pytest after: **301 passed, 1 skipped** in 34.65s.
- `TEST_SPLIT_TOUCH 0`: no model, threshold, or split changes.
- Every command ran with `PYTHONDONTWRITEBYTECODE=1`. Python cache hashes were unchanged during the final test run; separate cache comparison is `reports/b161_cache_diff.txt`.
- Exactly two existing root files were changed: `README.md` and `.gitignore`. No files in `medsafe/`, `models/`, `data/`, or `scripts/` were edited. Earlier B12 reports and tally script were left unchanged. No Git initialization, commit, or push was performed.

## 2. B12 tally reconciliation

- 25 unique pairs: 1 agree, 1 disagree, 19 unclear, 4 not retrievable.
- 0 of the 9 Major-labeled pairs had a definite answer.
- The prior total of 29 double-counted the four not-retrievable rows already included in the 23 unclear rows. Tally script lines 10 and 22–24 do not represent `not_retrievable` as its own category.
- Major estimates remain suppressed under the frozen rule.

Full source file counts, overlaps, code excerpt, and corrected tally: `reports/b161_tally_reconciliation.md`.

## 3. README and ignore rules

README was reconciled with `reports/b16_readme_draft.md`, preserving accurate existing source attribution and adding the requested limitations and current dose status. The checkout path and personal account name were removed. `.gitignore` now covers virtual environments, bytecode, test/tool caches, `.env`, and logs; neither `models/` nor `data/` is ignored.

The hygiene scan found no absolute path, personal name/email, phone number, API-key pattern, or AGENTS rule-7 banned phrase in `README.md` or `.gitignore`. The scan result is in `reports/b161_readme_scan.txt`; the full before/after diff is `reports/b161_readme_diff.patch`.

The README includes the exact requested sentence: “Allergy, drug-disease and dose rows come from drug labels and were checked against the label text by the project owner; this is not clinical review.” It immediately clarifies that no dose rows are loaded and that the source-text check applies to allergy and disease rows only.

## 4. Capability and deck-facts tables

Refreshed nine-capability evidence: `reports/b161_capability_evidence.md`. It records current exact product status words and the fake-client LLM run; no provider call or key was used.

Reconciled deck facts table: `reports/b161_deck_facts.md`. It includes 313 DDI rows, 30 distinct covered drugs, 174 `UNSPECIFIED`, 2 duplicate-policy, 5 allergy, 5 disease, 0 dose, whitelist 30, 13 verified brand mappings, DDInter counts, current test count, 9 withheld Major estimates, and the corrected B12 counts. All rows are counts and are marked OK to show as counts only; none supports an accuracy or clinical-performance claim.

## 5. Demo refresh

Each of the three synthetic demos was run three times. Every run was deterministic except `generated_at`; each normalized output matched its B16 snapshot. Comparison files: `reports/b161_demo_1_comparison.txt` through `reports/b161_demo_3_comparison.txt`. The first 40 lines of each rerun are in `reports/b161_demo_first40.md`; full outputs are `reports/b161_demo_1.txt` through `reports/b161_demo_3.txt`.

## 6. Commit preparation

- `models/`: 7,515,007 bytes; `data/`: 13,259,656 bytes.
- Raw DDInter directory: 13,135,540 bytes. Eight CSV sizes and all files over 5 MB are listed in `reports/b161_commit_prep.md`.
- Human decisions before public push: whether to redistribute the CC BY-NC-SA 4.0 raw DDInter files, whether the `work/b9_repro_20260930/` archive is needed, and whether to retain intentional reviewer names in B14 provenance files. Recommended actions and reasons are in the commit-prep report.
- No `.git/` directory exists. Exact init/review/key-scan/commit/push commands are printed in `reports/b161_commit_prep.md` and were not run. The remote URL and licensing decision remain owner inputs.

## 7. Not done

No clinical review, network or LLM provider call, new dependency, retraining, source-data change, feature change, Git initialization, commit, or push. The source spot check remains limited and does not validate ML estimates.
