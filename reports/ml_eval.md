# Offline DDInter severity-model evaluation

Severity labels are inherited from DDInter and map only its listed pair categories. No negative or unlisted pairs are treated as non-interactions.

## Split and validation-only selection

### RANDOM_PAIR

- Seed: 20260930; stratified where possible: True.
- Train/validation/test rows: 91,295/19,563/19,564.
- Drug partitions (train/validation/test): 1,877/1,758/1,747.
- Test-drug overlap with training-edge drugs: 1734.
- Selected on validation only: `hist_gradient_boosting`.
- Validation-frozen abstention threshold τ: 0.343390.

Validation candidate macro-F1 (selection metric):

| Candidate | Validation macro-F1 |
|---|---:|
| hist_gradient_boosting | 0.8449 |
| logistic_regression | 0.7319 |

### RANDOM_PAIR — validation — all validation pairs

| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |
|---|---:|---:|---|---|---|---:|---:|---:|
| hist_gradient_boosting | 19563 | 0.8449 | 0.829/0.888/0.857 | 0.963/0.917/0.939 | 0.631/0.889/0.738 | 0.1369 | 1.000 | 0.9091 |
| baseline:majority | 19563 | 0.2838 | 0.000/0.000/0.000 | 0.741/1.000/0.851 | 0.000/0.000/0.000 | 0.5175 | 1.000 | 0.7412 |
| baseline:per_drug_prior | 19563 | 0.5052 | 0.648/0.620/0.634 | 0.843/0.912/0.876 | 1.000/0.003/0.006 | 0.3916 | 1.000 | 0.8042 |

Confusion matrix for hist_gradient_boosting, labels `Major, Moderate, Minor`: `[[3583, 415, 39], [716, 13291, 494], [21, 93, 911]]`.
Confusion matrix for baseline:majority, labels `Major, Moderate, Minor`: `[[0, 4037, 0], [0, 14501, 0], [0, 1025, 0]]`.
Confusion matrix for baseline:per_drug_prior, labels `Major, Moderate, Minor`: `[[2504, 1533, 0], [1275, 13226, 0], [87, 935, 3]]`.

### RANDOM_PAIR — test — all test pairs

| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |
|---|---:|---:|---|---|---|---:|---:|---:|
| baseline:majority | 19564 | 0.2838 | 0.000/0.000/0.000 | 0.741/1.000/0.851 | 0.000/0.000/0.000 | 0.5175 | 1.000 | 0.7413 |
| baseline:per_drug_prior | 19564 | 0.5057 | 0.657/0.621/0.639 | 0.844/0.916/0.878 | 0.000/0.000/0.000 | 0.3854 | 1.000 | 0.8073 |
| hist_gradient_boosting | 19564 | 0.8446 | 0.827/0.905/0.864 | 0.968/0.914/0.940 | 0.623/0.881/0.730 | 0.1349 | 1.000 | 0.9102 |

Confusion matrix for baseline:majority, labels `Major, Moderate, Minor`: `[[0, 4037, 0], [0, 14502, 0], [0, 1025, 0]]`.
Confusion matrix for baseline:per_drug_prior, labels `Major, Moderate, Minor`: `[[2506, 1529, 2], [1214, 13288, 0], [92, 933, 0]]`.
Confusion matrix for hist_gradient_boosting, labels `Major, Moderate, Minor`: `[[3653, 335, 49], [752, 13252, 498], [13, 109, 903]]`.

Test pairs involving at least one whitelist drug: 1,105.
### RANDOM_PAIR — test — whitelist-drug subset

| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |
|---|---:|---:|---|---|---|---:|---:|---:|
| baseline:majority | 1105 | 0.2802 | 0.000/0.000/0.000 | 0.725/1.000/0.841 | 0.000/0.000/0.000 | 0.5502 | 1.000 | 0.7249 |
| baseline:per_drug_prior | 1105 | 0.4402 | 0.649/0.365/0.467 | 0.772/0.955/0.854 | 0.000/0.000/0.000 | 0.4814 | 1.000 | 0.7593 |
| hist_gradient_boosting | 1105 | 0.7612 | 0.739/0.823/0.779 | 0.935/0.839/0.884 | 0.506/0.802/0.621 | 0.2445 | 1.000 | 0.8326 |

Confusion matrix for baseline:majority, labels `Major, Moderate, Minor`: `[[0, 203, 0], [0, 801, 0], [0, 101, 0]]`.
Confusion matrix for baseline:per_drug_prior, labels `Major, Moderate, Minor`: `[[74, 129, 0], [36, 765, 0], [4, 97, 0]]`.
Confusion matrix for hist_gradient_boosting, labels `Major, Moderate, Minor`: `[[167, 28, 8], [58, 672, 71], [1, 19, 81]]`.


### COLD_DRUG

- Seed: 20260930; stratified where possible: True.
- Train/validation/test rows: 61,502/31,678/37,242.
- Drug partitions (train/validation/test): 1,331/285/286.
- Test-drug overlap with training-edge drugs: 0.
- Selected on validation only: `hist_gradient_boosting`.
- Validation-frozen abstention threshold τ: 1.010000.

Validation candidate macro-F1 (selection metric):

| Candidate | Validation macro-F1 |
|---|---:|
| hist_gradient_boosting | 0.2849 |
| logistic_regression | 0.1636 |

### COLD_DRUG — validation — all validation pairs

| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |
|---|---:|---:|---|---|---|---:|---:|---:|
| hist_gradient_boosting | 31678 | 0.2849 | 0.000/0.000/0.000 | 0.746/1.000/0.855 | 0.000/0.000/0.000 | 0.4321 | 0.000 | n/a |
| baseline:majority | 31678 | 0.2849 | 0.000/0.000/0.000 | 0.746/1.000/0.855 | 0.000/0.000/0.000 | 0.5073 | 0.000 | n/a |
| baseline:per_drug_prior | 31678 | 0.4297 | 0.674/0.306/0.421 | 0.791/0.962/0.868 | 0.000/0.000/0.000 | 0.4401 | 0.000 | n/a |

Confusion matrix for hist_gradient_boosting, labels `Major, Moderate, Minor`: `[[0, 6383, 0], [0, 23643, 0], [0, 1652, 0]]`.
Confusion matrix for baseline:majority, labels `Major, Moderate, Minor`: `[[0, 6383, 0], [0, 23643, 0], [0, 1652, 0]]`.
Confusion matrix for baseline:per_drug_prior, labels `Major, Moderate, Minor`: `[[1953, 4430, 0], [888, 22755, 0], [58, 1594, 0]]`.

### COLD_DRUG — test — all test pairs

| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |
|---|---:|---:|---|---|---|---:|---:|---:|
| baseline:majority | 37242 | 0.2824 | 0.000/0.000/0.000 | 0.735/1.000/0.847 | 0.000/0.000/0.000 | 0.5299 | 0.000 | n/a |
| baseline:per_drug_prior | 37242 | 0.4060 | 0.651/0.250/0.362 | 0.771/0.963/0.856 | 0.000/0.000/0.000 | 0.4782 | 0.000 | n/a |
| hist_gradient_boosting | 37242 | 0.2824 | 0.000/0.000/0.000 | 0.735/1.000/0.847 | 0.000/0.000/0.000 | 0.4557 | 0.000 | n/a |

Confusion matrix for baseline:majority, labels `Major, Moderate, Minor`: `[[0, 7863, 0], [0, 27374, 0], [0, 2005, 0]]`.
Confusion matrix for baseline:per_drug_prior, labels `Major, Moderate, Minor`: `[[1969, 5894, 0], [1005, 26369, 0], [51, 1954, 0]]`.
Confusion matrix for hist_gradient_boosting, labels `Major, Moderate, Minor`: `[[0, 7863, 0], [0, 27374, 0], [0, 2005, 0]]`.

Test pairs involving at least one whitelist drug: 1,596.
### COLD_DRUG — test — whitelist-drug subset

| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |
|---|---:|---:|---|---|---|---:|---:|---:|
| baseline:majority | 1596 | 0.2732 | 0.000/0.000/0.000 | 0.694/1.000/0.820 | 0.000/0.000/0.000 | 0.6115 | 0.000 | n/a |
| baseline:per_drug_prior | 1596 | 0.3285 | 0.611/0.095/0.165 | 0.705/0.981/0.820 | 0.000/0.000/0.000 | 0.5965 | 0.000 | n/a |
| hist_gradient_boosting | 1596 | 0.2732 | 0.000/0.000/0.000 | 0.694/1.000/0.820 | 0.000/0.000/0.000 | 0.5264 | 0.000 | n/a |

Confusion matrix for baseline:majority, labels `Major, Moderate, Minor`: `[[0, 346, 0], [0, 1108, 0], [0, 142, 0]]`.
Confusion matrix for baseline:per_drug_prior, labels `Major, Moderate, Minor`: `[[33, 313, 0], [21, 1087, 0], [0, 142, 0]]`.
Confusion matrix for hist_gradient_boosting, labels `Major, Moderate, Minor`: `[[0, 346, 0], [0, 1108, 0], [0, 142, 0]]`.


## Test-split access log

- `TEST_SPLIT_TOUCH RANDOM_PAIR: final evaluation reads held-out labels once; no model or threshold selection follows.`
- `TEST_SPLIT_TOUCH COLD_DRUG: final evaluation reads held-out labels once; no model or threshold selection follows.`

## Fixed gate

The gate is enabled only when RANDOM_PAIR test macro-F1 is at least the best baseline + 0.05 and RANDOM_PAIR Major recall is at least 0.50. COLD_DRUG does not affect the gate.

Result: **enabled**.

Precision on covered pairs is exact-label accuracy among pairs whose top probability reaches τ. A weak or disabled result remains an honest evaluation result; it does not change rule-based findings.

## Conclusion

- RANDOM_PAIR: `hist_gradient_boosting` beats best baseline on test (macro-F1 0.8446 vs 0.5057); Major recall 0.9049.
- COLD_DRUG: `hist_gradient_boosting` does not beat best baseline on test (macro-F1 0.2824 vs 0.4060); Major recall 0.0000.

## Post-hoc: threshold revised after the first test run; not used for selection

The revised threshold was selected from RANDOM_PAIR validation probabilities only. This post-hoc section applies it once to RANDOM_PAIR test predictions. It did not affect model selection or the gate. COLD_DRUG was not touched.

Validation rule: choose the smallest tau with covered accuracy >= 0.95, coverage >= 0.40, and Major-class precision among covered predictions >= 0.90; if none qualifies, set tau = 1.01.

- Threshold: 0.705426
- Test pairs: 19,564
- Covered pairs: 17,203
- Coverage: 0.8793
- Accuracy on covered pairs: 0.9499

| Predicted class | Precision among covered predictions | Predicted count | True positives |
|---|---:|---:|---:|
| Major | 0.9106 | 3,680 | 3,351 |
| Moderate | 0.9800 | 12,387 | 12,139 |
| Minor | 0.7491 | 1,136 | 851 |

