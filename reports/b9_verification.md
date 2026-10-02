# B9 verification record

Date: 2026-09-30. No network access used by B8/B9 pipeline or predictor. Public-source anecdotal checks are in `b9_anecdotal_checks.md`.

## Part A: B8 verification

### A1: artifact hash verification

| File | Manifest SHA-256 | Actual SHA-256 | Match |
|---|---|---|---|
| `models/severity_model.joblib` | `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` | `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` | yes |
| `models/drug_index.json` | `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c` | `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c` | yes |

### A2: allowlist and manifest changes; repository has no `.git` history

`models/drug_index.json` keys: `drugs, feature_version, listed_pairs, unlabeled_pairs, vector_columns, vector_size`. It contains 160,235 listed pairs and 29,813 Unknown-severity pairs. First 10 Unknown pairs: `[['abacavir', 'acetylsalicylic acid'], ['abacavir', 'acyclovir'], ['abacavir', 'amoxicillin'], ['abacavir', 'amphotericin b'], ['abacavir', 'atovaquone'], ['abacavir', 'budesonide'], ['abacavir', 'bupropion'], ['abacavir', 'celecoxib'], ['abacavir', 'cetirizine'], ['abacavir', 'clarithromycin']]`. The complete allowlist is in [models/drug_index.json](../models/drug_index.json).

`models/manifest.json` keys: `files, gate, listed_pair_count, model_name, raw_source_fingerprint, seed, tau, training_data_fingerprint, training_split, unlabeled_pair_count, versions`. Artifact file keys: `drug_index.json, severity_model.joblib`. B8 allowlist correction added `unlabeled_pairs` to the index and `unlabeled_pair_count` to the manifest; it updated the index checksum from the pre-correction `6dab2ffc5d1007f53b88be4f5fc1bb4e748cb74fde660d10aa1d26a90978f863` to `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c`. Model weights did not change. B9 later revised manifest `tau` from 0.3433901063 to 0.7054264739 under Part B.

### A3: reproducibility rerun

The full training script ran from an isolated temporary project copy and exited 0. It did not overwrite the shipped `models/` or `reports/`. The script's UTF-8 stdout configuration allowed it to finish cleanly.

| Value | Shipped | Reproduction | Result |
|---|---:|---:|---|
| Model SHA-256 | `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` | `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` | IDENTICAL |
| Original tau | 0.3433901063125201 | 0.3433901063125201 | IDENTICAL |
| RANDOM_PAIR model macro-F1 | 0.8446 | 0.8446 | IDENTICAL |
| RANDOM_PAIR best-baseline macro-F1 | 0.5057 | 0.5057 | IDENTICAL |
| COLD_DRUG model/baseline macro-F1 | 0.2824 / 0.4060 | 0.2824 / 0.4060 | IDENTICAL |

Reproduction access log: [reports/b9_reproducibility_access.log](b9_reproducibility_access.log).

### A4: evaluation table audit

All six `Model` tables have 9 header columns and 9 separator columns. Both whitelist-subset headings are followed directly by their tables. No report-generator or original evaluation-report edit was needed for A4 because checked output already meets the stated format.

## Part B: threshold revision

Exact rule: On RANDOM_PAIR validation, choose the smallest tau such that covered accuracy >= 0.95, coverage >= 0.40, and Major-class precision among covered predictions >= 0.90. If no tau qualifies, set tau = 1.01.

- Old tau: 0.3433901063125201.
- New tau: 0.7054264738830898.
- Validation coverage: 0.8754281041 (17,126/19,563).
- Validation covered accuracy: 0.9500175172.
- Validation Major precision on covered predictions: 0.9085635359.
- The selected model, model weights, features, and splits did not change.
- `ml_gate.json` records old/new tau, reason `original rule gave coverage 1.000`, `revised_after_test_run: true`, and the exact rule.
- RANDOM_PAIR post-hoc test section is in [reports/ml_eval.md](ml_eval.md); only RANDOM_PAIR test predictions/labels were read for that section. COLD_DRUG was not accessed post-hoc.

## Part C: report integration

Schema-only test run: 251 passed; final suite: 261 passed. Finding severity, rule id, ordering, and severity counts are unchanged between ML-on/off demo reports. The existing demo snapshot changed only to include the now-legitimate estimate on its `UNSPECIFIED` DDI finding; no assertions were weakened or removed.

Current `AGENTS.md` is updated to the final test count. CSV validator output and six B6.2 parser lines were present and are included in the final response.

