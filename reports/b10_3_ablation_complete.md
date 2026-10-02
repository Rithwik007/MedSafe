# B10.3 ablation completion

Analysis only. Ablation ran in a temporary copy and was deleted. No shipped model, threshold, gate, features, split files, evaluation report, or clinical CSV changed. No network or LLM calls; no dependencies added.

## Feature audit

`DrugVectors` columns removed (direct per-drug label history): `major_fraction`, `moderate_fraction`, `minor_fraction`.

`DrugVectors` columns kept: `degree`, `svd_1`, `svd_2`, `svd_3`, `svd_4`, `svd_5`, `svd_6`, `svd_7`, `svd_8`, `svd_9`, `svd_10`, `svd_11`, `svd_12`, `svd_13`, `svd_14`, `svd_15`, `svd_16`.

`pair_features` returns an unnamed NumPy array. The following exact readable names map its concatenated columns (`a+b`, `abs(a-b)`, `a*b`, then scalar features).

Removed pair columns (9): `sum_major_fraction`, `sum_moderate_fraction`, `sum_minor_fraction`, `absdiff_major_fraction`, `absdiff_moderate_fraction`, `absdiff_minor_fraction`, `product_major_fraction`, `product_moderate_fraction`, `product_minor_fraction`.

Kept pair columns (54):

- Sum: `sum_degree`, `sum_svd_1`, `sum_svd_2`, `sum_svd_3`, `sum_svd_4`, `sum_svd_5`, `sum_svd_6`, `sum_svd_7`, `sum_svd_8`, `sum_svd_9`, `sum_svd_10`, `sum_svd_11`, `sum_svd_12`, `sum_svd_13`, `sum_svd_14`, `sum_svd_15`, `sum_svd_16`.
- Absolute difference: `absdiff_degree`, `absdiff_svd_1`, `absdiff_svd_2`, `absdiff_svd_3`, `absdiff_svd_4`, `absdiff_svd_5`, `absdiff_svd_6`, `absdiff_svd_7`, `absdiff_svd_8`, `absdiff_svd_9`, `absdiff_svd_10`, `absdiff_svd_11`, `absdiff_svd_12`, `absdiff_svd_13`, `absdiff_svd_14`, `absdiff_svd_15`, `absdiff_svd_16`.
- Product: `product_degree`, `product_svd_1`, `product_svd_2`, `product_svd_3`, `product_svd_4`, `product_svd_5`, `product_svd_6`, `product_svd_7`, `product_svd_8`, `product_svd_9`, `product_svd_10`, `product_svd_11`, `product_svd_12`, `product_svd_13`, `product_svd_14`, `product_svd_15`, `product_svd_16`.
- Other: `min_degree`, `max_degree`, `unseen_drug_count`.

## SVD and split audit

SVD uses **severity-weighted adjacency**, not binary adjacency. `medsafe/ml/features.py:38-55` assigns Major=3, Moderate=2, Minor=1, builds adjacency from each `train_edges` row, then fits `TruncatedSVD` on that matrix. `medsafe/ml/training.py:134-140` passes only `split.train` into `fit_drug_vectors`; validation pairs are transformed after fit. The ablation child likewise fits vectors from `train` only (`scripts/run_ml_ablation_b10_2.py:67-72`). No validation/test edges enter SVD. No SVD leakage found.

The established stratified RANDOM_PAIR partition was reproduced. Only train and validation rows entered ablation fitting, tau selection, and metrics. Reserved test rows were not scored or evaluated. `TEST_SPLIT_TOUCH count: 0` (no test outcome read or metric computed).

## RANDOM_PAIR validation

Validation rows: 19,563. Metrics use raw argmax labels; tau controls coverage only. Confusion matrix order: true rows and predicted columns `[Major, Moderate, Minor]`.

| Model | Tau | Macro-F1 | Class | Precision | Recall | F1 |
|---|---:|---:|---|---:|---:|---:|
| Shipped | 0.705426 | 0.8449 | Major | 0.8294 | 0.8875 | 0.8575 |
| Shipped | 0.705426 | 0.8449 | Moderate | 0.9632 | 0.9166 | 0.9393 |
| Shipped | 0.705426 | 0.8449 | Minor | 0.6309 | 0.8888 | 0.7380 |
| Ablated | 0.727988 | 0.7603 | Major | 0.7758 | 0.8434 | 0.8082 |
| Ablated | 0.727988 | 0.7603 | Moderate | 0.9513 | 0.8559 | 0.9010 |
| Ablated | 0.727988 | 0.7603 | Minor | 0.4236 | 0.8790 | 0.5717 |

| Model | Brier |
|---|---:|
| Shipped | 0.1369 |
| Ablated | 0.2148 |

| Model | Confusion matrix |
|---|---|
| Shipped | `[3583, 415, 39]; [716, 13291, 494]; [21, 93, 911]` |
| Ablated | `[3405, 529, 103]; [967, 12411, 1123]; [17, 107, 901]` |

## Unknown-pair matched coverage

Pool: all 29,813 DDInter Unknown pairs. Applied the same serving eligibility check to both models: both drugs in model vectors, pair in listed set, and pair in unlabeled set. Coverage denominator is the full Unknown pool. Matched comparisons select highest-confidence eligible pairs up to the other model's covered count; this rank selection is analysis-only. No threshold saved or tuned.

| Model at its validation tau | Covered | Coverage | Major | KCl Major | KCl share of Major |
|---|---:|---:|---:|---:|---:|
| Shipped | 20,446 | 68.58% | 734 | 165 | 22.48% |
| Ablated | 9,112 | 30.56% | 164 | 28 | 17.07% |

| Matched comparison | Covered target | Major | KCl Major | KCl share of Major |
|---|---:|---:|---:|---:|
| Shipped at ablated coverage | 9,112 | 139 | 31 | 22.30% |
| Ablated at shipped coverage | 20,446 | 431 | 66 | 15.31% |

Major-pair overlap at each model's own validation tau: **109 both, 625 shipped only, 55 ablated only**.

B10.2's ablated Unknown coverage scored every pair directly, including rows outside the serving eligibility check. Applying the same eligibility rule here leaves 9,112 covered pairs, versus 10,287 in that earlier diagnostic; 10 earlier ablated Major estimates also fall outside serving eligibility. This corrects the coverage comparison. It does not show accuracy on Unknown pairs.

## Validation slice by potassium chloride

Raw argmax Major precision/recall; validation has only 15 pairs containing potassium chloride (9 true Major), so treat this slice as small.

| Model | Validation subset | Pairs | Major TP | FP | FN | Major precision | Major recall |
|---|---|---:|---:|---:|---:|---:|---:|
| Shipped | Contains KCl | 15 | 9 | 1 | 0 | 0.9000 | 1.0000 |
| Shipped | No KCl | 19,548 | 3,574 | 736 | 454 | 0.8292 | 0.8873 |
| Ablated | Contains KCl | 15 | 9 | 0 | 0 | 1.0000 | 1.0000 |
| Ablated | No KCl | 19,548 | 3,396 | 984 | 632 | 0.7753 | 0.8431 |

These are measurements, not evidence of pharmacology or clinical validity.

## Artifact checksums

| Artifact | Actual SHA-256 | Manifest SHA-256 | Match |
|---|---|---|---|
| `drug_index.json` | `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c` | `1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c` | Yes |
| `severity_model.joblib` | `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` | `3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c` | Yes |

No tests or assertions changed. No spot-check review columns or clinical CSVs changed. No source checks were performed.
