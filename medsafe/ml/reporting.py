"""Render full audit, evaluation, gate, and model-card text artifacts."""
from __future__ import annotations

from typing import Any

from medsafe.ml.config import (EMBEDDING_DIMS, GATE_MACRO_F1_MARGIN,
    GATE_MAJOR_RECALL_MIN, MIN_COVERAGE, SEED)
from medsafe.ml.data import DataAudit
from medsafe.ml.training import PreparedExperiment


def _p(value: Any) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _metric_rows(split_name: str, phase: str, models: dict[str, dict[str, Any]],
                 subset: str) -> list[str]:
    lines = [f"### {split_name} — {phase} — {subset}", "",
        "| Model | n | Macro-F1 | Major P/R/F1 | Moderate P/R/F1 | Minor P/R/F1 | Brier | Coverage @ τ | Precision on covered |",
        "|---|---:|---:|---|---|---|---:|---:|---:|"]
    for name, metric in models.items():
        classes = metric["per_class"]
        def prf(label: str) -> str:
            item = classes[label]
            return f"{item['precision']:.3f}/{item['recall']:.3f}/{item['f1']:.3f}"
        lines.append(f"| {name} | {metric['n']} | {metric['macro_f1']:.4f} | {prf('Major')} | "
            f"{prf('Moderate')} | {prf('Minor')} | {metric['brier_score']:.4f} | "
            f"{metric['coverage_at_tau']:.3f} | {_p(metric['precision_on_covered'])} |")
    lines.append("")
    for name, metric in models.items():
        lines.append(f"Confusion matrix for {name}, labels `{', '.join(metric['confusion_labels'])}`: "
                     f"`{metric['confusion_matrix']}`.")
    lines.append("")
    return lines


def render_evaluation(prepared: dict[str, PreparedExperiment],
                      test_results: dict[str, dict[str, dict[str, Any]]],
                      whitelist_counts: dict[str, int], touch_lines: list[str],
                      gate: dict[str, Any]) -> str:
    lines = ["# Offline DDInter severity-model evaluation", "",
        "Severity labels are inherited from DDInter and map only its listed pair categories. "
        "No negative or unlisted pairs are treated as non-interactions.", "",
        "## Split and validation-only selection", ""]
    for name, experiment in prepared.items():
        split = experiment.split
        training_edge_drugs = set(split.train["drug_a"]) | set(split.train["drug_b"])
        lines += [f"### {name}", "",
            f"- Seed: {SEED}; stratified where possible: {split.stratified}.",
            f"- Train/validation/test rows: {len(split.train):,}/{len(split.validation):,}/"
            f"{test_results[name][experiment.chosen_name]['all']['n']:,}.",
            f"- Drug partitions (train/validation/test): {len(split.train_drugs):,}/"
            f"{len(split.validation_drugs):,}/{len(split.test_drugs):,}.",
            f"- Test-drug overlap with training-edge drugs: {len(split.test_drugs & training_edge_drugs)}.",
            f"- Selected on validation only: `{experiment.chosen_name}`.",
            f"- Validation-frozen abstention threshold τ: {experiment.tau:.6f}.", "",
            "Validation candidate macro-F1 (selection metric):", "",
            "| Candidate | Validation macro-F1 |", "|---|---:|"]
        for candidate in ("hist_gradient_boosting", "logistic_regression"):
            lines.append(f"| {candidate} | {experiment.validation_scores[candidate]['macro_f1']:.4f} |")
        val_models = {key: value for key, value in experiment.validation_scores.items()
                      if key.startswith("baseline:") or key == experiment.chosen_name}
        lines += ["", *_metric_rows(name, "validation", val_models, "all validation pairs")]
        test_models = test_results[name]
        lines += _metric_rows(name, "test", {key: value["all"] for key, value in test_models.items()},
                              "all test pairs")
        subset_models = {key: value["whitelist_subset"] for key, value in test_models.items()
                         if value["whitelist_subset"] is not None}
        lines.append(f"Test pairs involving at least one whitelist drug: {whitelist_counts[name]:,}.")
        if subset_models:
            lines += _metric_rows(name, "test", subset_models, "whitelist-drug subset")
        else:
            lines.append("Whitelist-drug subset has zero rows; metrics unavailable.")
        lines.append("")
    lines += ["## Test-split access log", ""]
    lines.extend(f"- `{line}`" for line in touch_lines)
    lines += ["", "## Fixed gate", "",
        f"The gate is enabled only when RANDOM_PAIR test macro-F1 is at least the best baseline + "
        f"{GATE_MACRO_F1_MARGIN:.2f} and RANDOM_PAIR Major recall is at least "
        f"{GATE_MAJOR_RECALL_MIN:.2f}. COLD_DRUG does not affect the gate.", "",
        f"Result: **{'enabled' if gate['enabled'] else 'disabled'}**.", "",
        "Precision on covered pairs is exact-label accuracy among pairs whose top probability reaches τ. "
        "A weak or disabled result remains an honest evaluation result; it does not change rule-based findings.", ""]
    for name, experiment in prepared.items():
        model_metric = test_results[name][experiment.chosen_name]["all"]
        baseline_metrics = [test_results[name][f"baseline:{baseline}"]["all"]
                            for baseline in experiment.baseline_names]
        best_baseline = max(item["macro_f1"] for item in baseline_metrics)
        outcome = "beats" if model_metric["macro_f1"] > best_baseline else "does not beat"
        lines.append(f"- {name}: `{experiment.chosen_name}` {outcome} best baseline on test "
            f"(macro-F1 {model_metric['macro_f1']:.4f} vs {best_baseline:.4f}); "
            f"Major recall {model_metric['major_recall']:.4f}.")
    lines.append("")
    return "\n".join(lines)


def render_model_card(audit: DataAudit, gate: dict[str, Any], eval_text: str,
                      model_name: str, tau: float,
                      test_results: dict[str, dict[str, dict[str, Any]]]) -> str:
    random = gate["random_pair_test"]
    cold_model = test_results["COLD_DRUG"]["hist_gradient_boosting"]["all"]
    cold_baseline = max(test_results["COLD_DRUG"][f"baseline:{name}"]["all"]["macro_f1"]
                        for name in ("majority", "per_drug_prior"))
    return f"""# MedSafe DDInter severity model card

## Purpose

Offline research prototype predicts a severity label only for DDInter-listed pairs whose source severity is Unknown. Predictor checks a local allowlist of {len(audit.unlabeled_pairs):,} Unknown-severity pairs and cannot discover new interactions. DDInter absence is not evidence of no interaction. Model prediction never changes rule-based findings.

## Data and license

Source is the full local DDInter CSV set, with {audit.total_rows_read:,} source rows and {len(audit.unique_pairs):,} unique canonical pairs. DDInter is attributed to the Computational Biology & Drug Design Group: https://ddinter.scbdd.com/download/. Source data and this derivative model are distributed under CC BY-NC-SA 4.0; preserve attribution and share-alike terms. No network source was accessed during training.

Unknown-severity pairs are excluded from supervised training. There are {len(audit.unlabeled_pairs):,} unique Unknown pairs ({audit.unknown_share:.2%} of all unique pairs). Accuracy on Unknown-severity pairs cannot be verified and may differ from labeled pairs.

## Labels and splits

Labels: Major, Moderate, Minor, using DDInter's supplied severity. Unknown is unlabeled, not a target class. Pair-random and cold-drug splits use seed {SEED}, with 70/15/15 targets. Cold split holds out drugs; every edge involving validation or test drugs is kept out of training. See `reports/ml_eval.md` for metrics and actual edge counts.

## Features and model

Features use training edges only: degree, training-severity fractions, {EMBEDDING_DIMS} seeded TruncatedSVD dimensions from severity-weighted adjacency, and symmetric sum, absolute difference, product, min/max degree, and unseen-drug count for each pair. An unseen cold-split drug gets an all-zero vector and unseen flag. ATC class features were skipped: `drug_classes.csv` covers only the 30-drug whitelist, below 80% of {len(audit.unique_drugs):,} DDInter drugs. No external data or network calls are used.

Validation selected `{model_name}`. Abstention threshold τ uses validation-only covered accuracy >=0.95, coverage >=0.40, and Major precision >=0.90; selected τ: {tau:.6f}. Gate enabled: {str(gate['enabled']).lower()}. RANDOM_PAIR test macro-F1: {random['model_macro_f1']:.4f}; best-baseline macro-F1: {random['best_baseline_macro_f1']:.4f}; Major recall: {random['major_recall']:.4f}. Full evaluation: `reports/ml_eval.md`.

COLD_DRUG test macro-F1 is {cold_model['macro_f1']:.4f} versus best baseline {cold_baseline:.4f}; Major recall is {cold_model['major_recall']:.4f}. The model does not beat the cold-drug baseline and does not demonstrate generalization to unseen drugs.

## Limitations

- Training-pair features include each training pair's own label through the adjacency used to build graph features. Out-of-fold features would remove this training-time information; test edges remain excluded from feature fitting.
- Unknown pairs are {audit.raw_label_counts.get('Unknown', 0) / max(audit.total_rows_read, 1) * 100:.1f} percent of raw DDInter rows overall and {audit.demo_raw_unknown_share * 100:.1f} percent of pairs among the 30 demo drugs, so the model is used where labels are scarcest.
- Revised abstention threshold was chosen on validation only. Post-hoc test metrics are descriptive and were not used for threshold selection.
- Predicts severity only for DDInter-listed pairs whose source severity is Unknown; cannot discover new interactions. Already labeled DDInter pairs remain unchanged.
- DDInter absence is not evidence of no interaction.
- Accuracy on Unknown-severity pairs cannot be verified and may differ from labeled pairs.
- This prototype is not for clinical use. Predictions are ML-PREDICTED and unverified. Rule-based severity and findings remain authoritative.
"""
