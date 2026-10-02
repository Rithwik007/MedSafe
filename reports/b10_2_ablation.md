# B10.2 own-label-feature ablation

Ablation ran in a temporary copy, deleted after completion. HistGradientBoosting model family, seed, and RANDOM_PAIR train/validation split match the shipped workflow. Only direct per-drug severity-fraction dimensions and their pairwise sum, absolute-difference, and product columns were removed. No test metric was computed.

drug_index.json vector_columns: degree, major_fraction, moderate_fraction, minor_fraction, svd_1, svd_2, svd_3, svd_4, svd_5, svd_6, svd_7, svd_8, svd_9, svd_10, svd_11, svd_12, svd_13, svd_14, svd_15, svd_16.
Removed direct per-drug label-history dimensions: major_fraction, moderate_fraction, minor_fraction, including their derived sum/difference/product columns. Degree and SVD retained. SVD embeds severity-weighted training adjacency and may retain indirect label-pattern information; this is not a full label-information ablation.

## RANDOM_PAIR validation metrics

| Model | Tau | Macro-F1 | Major P | Major R | Major F1 | Brier | Confusion matrix [Major, Moderate, Minor] |
|---|---:|---:|---:|---:|---:|---:|---|
| Shipped | 0.705426 | 0.8449 | 0.8294 | 0.8875 | 0.8575 | 0.1369 | 3583,415,39; 716,13291,494; 21,93,911 |
| Ablated | 0.727988 | 0.7603 | 0.7758 | 0.8434 | 0.8082 | 0.2148 | 3405,529,103; 967,12411,1123; 17,107,901 |

## Unknown-pair estimates (unlabeled; descriptive only)

| Model | Major count | Major share of all Unknown | KCl Major count | KCl share of Major estimates | Abstained share | Spearman rho (whitelist predicted vs training Major share) |
|---|---:|---:|---:|---:|---:|---:|
| Shipped | 734 | 0.0246 | 165 | 0.2248 | 0.3142 | 0.6511 |
| Ablated | 174 | 0.0058 | 28 | 0.1609 | 0.6549 | 0.0163 |

Major-estimate pair overlap: 109.

Validation macro-F1 change, ablated minus shipped: -0.0846.
Measurements only; ablation does not establish cause and does not validate predictions on unlabeled pairs.

## Shipped model checksum verification

- drug_index.json: actual SHA-256 1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c; manifest 1dc42194e33bc8be529ba44207b0738d94c3a524d14b2f8be504271727216e4c; match=True.
- severity_model.joblib: actual SHA-256 3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c; manifest 3c143a3e4f3adffeb3940a4d65018e895cdb877e3b17152a409bcc52601d705c; match=True.

TEST_SPLIT_TOUCH count: 0.

