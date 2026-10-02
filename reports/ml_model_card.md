# MedSafe DDInter severity model card

## Purpose

Offline research prototype predicts a severity label only for DDInter-listed pairs whose source severity is Unknown. Predictor checks a local allowlist of 29,813 Unknown-severity pairs and cannot discover new interactions. DDInter absence is not evidence of no interaction. Model prediction never changes rule-based findings.

## Data and license

Source is the full local DDInter CSV set, with 222,383 source rows and 160,235 unique canonical pairs. DDInter is attributed to the Computational Biology & Drug Design Group: https://ddinter.scbdd.com/download/. Source data and this derivative model are distributed under CC BY-NC-SA 4.0; preserve attribution and share-alike terms. No network source was accessed during training.

Unknown-severity pairs are excluded from supervised training. There are 29,813 unique Unknown pairs (18.61% of all unique pairs). Accuracy on Unknown-severity pairs cannot be verified and may differ from labeled pairs.

## Labels and splits

Labels: Major, Moderate, Minor, using DDInter's supplied severity. Unknown is unlabeled, not a target class. Pair-random and cold-drug splits use seed 20260930, with 70/15/15 targets. Cold split holds out drugs; every edge involving validation or test drugs is kept out of training. See `reports/ml_eval.md` for metrics and actual edge counts.

## Features and model

Features use training edges only: degree, training-severity fractions, 16 seeded TruncatedSVD dimensions from severity-weighted adjacency, and symmetric sum, absolute difference, product, min/max degree, and unseen-drug count for each pair. An unseen cold-split drug gets an all-zero vector and unseen flag. ATC class features were skipped: `drug_classes.csv` covers only the 30-drug whitelist, below 80% of 1,939 DDInter drugs. No external data or network calls are used.

Validation selected `hist_gradient_boosting`. Original threshold 0.343390 produced 1.000 coverage and was revised after the first test run. Revised tau 0.705426 was selected on RANDOM_PAIR validation only by requiring covered accuracy >=0.95, coverage >=0.40, and Major precision >=0.90. The post-hoc test result is not used for selection. Gate enabled: true. RANDOM_PAIR test macro-F1: 0.8446; best-baseline macro-F1: 0.5057; Major recall: 0.9049. Full evaluation: `reports/ml_eval.md`.

COLD_DRUG test macro-F1 is 0.2824 versus best baseline 0.4060; Major recall is 0.0000. The model does not beat the cold-drug baseline.

## Limitations

### Dose checker conventions

- D1: blank age bounds are used only when the label population text says "age range not stated by label". This wording records a label limitation; it is not an age range inferred by the project.
- D2: adult rows are checked only when age_years is supplied and at least 18. Missing age and age below 18 stay unresolved.
- D3: the checker abstains unless parse confidence is HIGH, units per intake and frequency are known, order and row units match exactly, the order is neither as-needed nor one-time, and route matches. No unit conversion is used.
- D4: each order is checked alone. Amounts from separate orders are not combined.
- D5: only an exceeded single or daily row limit creates an UNSPECIFIED finding. The finding shows the computed daily total and source row limit, then asks for pharmacist review. No reassurance is emitted for other results.

### Observed model behavior (2026-10-01)

Observed in the current analysis: 8 of 9 Major estimates on UNSPECIFIED rules involve potassium chloride; cold-drug macro-F1 0.2824 versus baseline 0.4060; validation-only ablation macro-F1 0.7603 versus shipped validation macro-F1 0.8449. These are dataset measurements. They do not establish why estimates occur or validate Unknown-pair predictions against outside sources.

### Unknown-pair prediction concentration (observational)

Across 29,813 DDInter Unknown pairs, the shipped model assigned Major to 734 (2.5%) and abstained on 9,367 (31.4%). Among Unknown pairs involving whitelist drugs, potassium chloride had 165 Major estimates among 412 pairs (40.0%); it accounted for 165 of all 734 Major estimates (22.5%). Its share of Major among labeled RANDOM_PAIR training edges was 72.5%. Across the 29 whitelist drugs with nonzero Unknown and labeled-training denominators, per-drug predicted-Major share and labeled training-Major share had Spearman rho 0.6511 (p=0.0001306). This is a distributional observation from DDInter-derived data; it does not establish why the model produced these estimates or validate them clinically. See `reports/ml_unknown_distribution.md`.

- Training-pair features include each training pair's own label through the adjacency used to build graph features. Out-of-fold features would remove this training-time information; test edges remain excluded from feature fitting.
- Unknown pairs are 21.2 percent of raw DDInter rows overall and 54.6 percent of pairs among the 30 demo drugs, so the model is used where labels are scarcest.
- Cold-drug evaluation failed to beat the baseline; the model does not demonstrate generalization to unseen drugs.
- Revised abstention threshold was chosen on validation only. The post-hoc test metrics are descriptive and were not used for threshold selection.
- Predicts severity only for DDInter-listed pairs whose source severity is Unknown; cannot discover new interactions. Already labeled DDInter pairs remain unchanged.
- DDInter absence is not evidence of no interaction.
- Accuracy on Unknown-severity pairs cannot be verified and may differ from labeled pairs.
- This prototype is not for clinical use. Predictions are ML-PREDICTED and unverified. Rule-based severity and findings remain authoritative.

### Outside-source spot check and B13 policy (2026-10-01)

The B12 spot-check tally recorded 1 agree, 1 disagree, 23 unclear, and 4 not retrievable. Of the 9 estimates labeled Major on `UNSPECIFIED` rules, 0 received a definite outside-source answer. The frozen rule requires at least 3 definite Major rows, so B13 withholds all Major ML estimates. This policy acts after prediction and before note attachment. It leaves model artifacts, tau, rule-based findings, and Moderate and Minor estimates unchanged. It reports only a class-free withheld count.

Limitations of this check: the rule file was saved after research started; predicted labels were visible during research; only 25 distinct pairs were in scope; unclear is not agreement; Drugs.com absence is not proof of no interaction; and the acetaminophen + ibuprofen “disagree” row is unverified. Four pairs were not retrievable. The tally is weak evidence and does not establish prediction accuracy or clinical validity.



