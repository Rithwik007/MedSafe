"""Seeded baselines, validation-only model selection, and final metrics."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from medsafe.ml.config import (GATE_MACRO_F1_MARGIN, GATE_MAJOR_RECALL_MIN,
    MAJOR_PRECISION_TARGET, MIN_COVERAGE, MIN_COVERED_ACCURACY, SEED, SEVERITIES,
    SEVERITY_ORDER)
from medsafe.ml.features import DrugVectors, fit_drug_vectors, pair_matrix
from medsafe.ml.splits import DataSplit, make_splits


@dataclass
class PreparedExperiment:
    name: str
    split: DataSplit
    drug_vectors: DrugVectors
    candidates: dict[str, Any]
    validation_scores: dict[str, dict[str, Any]]
    chosen_name: str
    chosen_model: Any
    tau: float
    validation_probabilities: np.ndarray
    baseline_names: tuple[str, ...]


def majority_label(train: pd.DataFrame) -> str:
    counts = train["severity"].value_counts().to_dict()
    return max(SEVERITIES, key=lambda label: (counts.get(label, 0), SEVERITY_ORDER[label]))


def per_drug_priors(train: pd.DataFrame) -> dict[str, str]:
    counts: dict[str, dict[str, int]] = {}
    for edge in train.itertuples(index=False):
        for drug in {edge.drug_a, edge.drug_b}:
            counts.setdefault(drug, {}).setdefault(edge.severity, 0)
            counts[drug][edge.severity] += 1
    return {drug: max(SEVERITIES, key=lambda label: (by_label.get(label, 0), SEVERITY_ORDER[label]))
            for drug, by_label in counts.items()}


def baseline_predictions(train: pd.DataFrame, pairs: pd.DataFrame,
                         baseline: str) -> np.ndarray:
    fallback = majority_label(train)
    if baseline == "majority":
        return np.full(len(pairs), fallback, dtype=object)
    priors = per_drug_priors(train)
    predictions = []
    for row in pairs.itertuples(index=False):
        left = priors.get(row.drug_a, fallback)
        right = priors.get(row.drug_b, fallback)
        predictions.append(max((left, right), key=lambda label: SEVERITY_ORDER[label]))
    return np.asarray(predictions, dtype=object)


def make_classifier(name: str, seed: int = SEED):
    if name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(class_weight="balanced", random_state=seed,
                                               max_iter=100)
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced",
            max_iter=1000, random_state=seed, solver="lbfgs"))
    raise ValueError(f"Unknown classifier: {name}")


def _all_class_probabilities(model: Any, matrix: np.ndarray) -> np.ndarray:
    raw = model.predict_proba(matrix)
    aligned = np.zeros((len(matrix), len(SEVERITIES)), dtype=np.float64)
    for source_column, label in enumerate(model.classes_):
        aligned[:, SEVERITIES.index(str(label))] = raw[:, source_column]
    return aligned


def choose_tau(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    top = probabilities.max(axis=1)
    top_index = probabilities.argmax(axis=1)
    predicted = np.asarray(SEVERITIES, dtype=object)[top_index]
    for tau in sorted(set(float(value) for value in top)):
        covered = top >= tau
        if covered.mean() < MIN_COVERAGE:
            continue
        if np.mean(predicted[covered] == y_true[covered]) < MIN_COVERED_ACCURACY:
            continue
        predicted_major = covered & (top_index == SEVERITIES.index("Major"))
        denominator = int(predicted_major.sum())
        major_precision = (float(np.sum(predicted_major & (y_true == "Major"))) / denominator
                           if denominator else 0.0)
        if major_precision >= MAJOR_PRECISION_TARGET:
            return tau
    return 1.01


def _one_hot(labels: np.ndarray) -> np.ndarray:
    result = np.zeros((len(labels), len(SEVERITIES)), dtype=np.float64)
    for index, label in enumerate(labels):
        result[index, SEVERITIES.index(str(label))] = 1.0
    return result


def metrics(y_true: np.ndarray, probabilities: np.ndarray, tau: float) -> dict[str, Any]:
    predicted = np.asarray(SEVERITIES, dtype=object)[probabilities.argmax(axis=1)]
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, predicted,
        labels=list(SEVERITIES), zero_division=0)
    top = probabilities.max(axis=1)
    covered = top >= tau
    covered_precision = float(np.mean(predicted[covered] == y_true[covered])) if covered.any() else None
    major_index = SEVERITIES.index("Major")
    cm = confusion_matrix(y_true, predicted, labels=list(SEVERITIES)).tolist()
    brier = float(np.mean(np.sum((probabilities - _one_hot(y_true)) ** 2, axis=1)))
    return {"n": int(len(y_true)), "macro_f1": float(f1_score(y_true, predicted,
        labels=list(SEVERITIES), average="macro", zero_division=0)),
        "per_class": {label: {"precision": float(precision[i]), "recall": float(recall[i]),
                              "f1": float(f1[i])} for i, label in enumerate(SEVERITIES)},
        "major_recall": float(recall[major_index]), "major_precision": float(precision[major_index]),
        "confusion_matrix": cm, "confusion_labels": list(SEVERITIES),
        "coverage_at_tau": float(covered.mean()), "precision_on_covered": covered_precision,
        "brier_score": brier}


def _baseline_probabilities(predictions: np.ndarray) -> np.ndarray:
    return _one_hot(predictions)


def prepare_experiment(name: str, split: DataSplit, seed: int = SEED) -> PreparedExperiment:
    # Only split.train reaches the graph-statistic and embedding fit function.
    vectors = fit_drug_vectors(split.train, seed=seed)
    x_train = pair_matrix(split.train, vectors)
    x_val = pair_matrix(split.validation, vectors)
    y_train = split.train["severity"].to_numpy(dtype=object)
    y_val = split.validation["severity"].to_numpy(dtype=object)

    baseline_names = ("majority", "per_drug_prior")
    # Baselines are evaluated on validation before candidate classifiers.
    val_baselines = {baseline: baseline_predictions(split.train, split.validation, baseline)
                     for baseline in baseline_names}
    baseline_validation = {name: metrics(y_val, _baseline_probabilities(pred), 0.0)
                           for name, pred in val_baselines.items()}

    candidates: dict[str, Any] = {}
    validation_scores: dict[str, dict[str, Any]] = {}
    probabilities: dict[str, np.ndarray] = {}
    for model_name in ("hist_gradient_boosting", "logistic_regression"):
        model = make_classifier(model_name, seed)
        model.fit(x_train, y_train)
        candidates[model_name] = model
        probabilities[model_name] = _all_class_probabilities(model, x_val)
        validation_scores[model_name] = metrics(y_val, probabilities[model_name], 0.0)

    chosen_name = max(validation_scores,
        key=lambda candidate: validation_scores[candidate]["macro_f1"])
    chosen_model = candidates[chosen_name]
    tau = choose_tau(y_val, probabilities[chosen_name])
    validation_probabilities = probabilities[chosen_name]
    validation_scores[chosen_name] = metrics(y_val, validation_probabilities, tau)
    validation_scores.update({f"baseline:{key}": metrics(y_val,
        _baseline_probabilities(val_baselines[key]), tau) for key in baseline_names})
    return PreparedExperiment(name, split, vectors, candidates, validation_scores,
        chosen_name, chosen_model, tau, validation_probabilities, baseline_names)


def evaluate_test_once(prepared: PreparedExperiment, whitelist: set[str],
                       log_lines: list[str]) -> dict[str, dict[str, Any]]:
    message = (f"TEST_SPLIT_TOUCH {prepared.name}: final evaluation reads held-out labels once; "
               "no model or threshold selection follows.")
    logging.info(message)
    log_lines.append(message)
    test_pairs = prepared.split.test
    y_test = test_pairs["severity"].to_numpy(dtype=object)
    x_test = pair_matrix(test_pairs, prepared.drug_vectors)
    outputs: dict[str, np.ndarray] = {
        f"baseline:{baseline}": _baseline_probabilities(
            baseline_predictions(prepared.split.train, test_pairs, baseline))
        for baseline in prepared.baseline_names}
    outputs[prepared.chosen_name] = _all_class_probabilities(prepared.chosen_model, x_test)
    results: dict[str, dict[str, Any]] = {}
    mask = (test_pairs["drug_a"].str.casefold().isin(whitelist)
            | test_pairs["drug_b"].str.casefold().isin(whitelist)).to_numpy()
    for name, probabilities in outputs.items():
        tau = prepared.tau
        results[name] = {"all": metrics(y_test, probabilities, tau)}
        results[name]["whitelist_subset"] = metrics(y_test[mask], probabilities[mask], tau) if mask.any() else None
    return results
