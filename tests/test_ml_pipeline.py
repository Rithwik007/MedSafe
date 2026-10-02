import json
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from medsafe.ml.data import load_ddinter
from medsafe.ml.features import DrugVectors, fit_drug_vectors, pair_features
from medsafe.ml.splits import cold_drug_split, make_splits
from medsafe.ml.training import choose_tau, make_classifier

FIXTURE = Path(__file__).parent / "fixtures" / "ml"


def _edge_table(size=16):
    labels = ("Major", "Moderate", "Minor")
    rows = []
    for left in range(size):
        for right in range(left + 1, size):
            rows.append({"drug_a": f"drug_{left:02}", "drug_b": f"drug_{right:02}",
                         "severity": labels[(left * 7 + right) % len(labels)]})
    return pd.DataFrame(rows)


def test_ddinter_pairs_canonicalize_dedupe_keep_highest_and_separate_unknown(caplog):
    audit = load_ddinter(FIXTURE / "raw", FIXTURE / "whitelist.csv")
    assert audit.total_rows_read == 5
    assert len(audit.unique_pairs) == 4
    pair = audit.unique_pairs.query("drug_a == 'drug_a' and drug_b == 'drug_b'")
    assert pair.iloc[0]["severity"] == "Major"
    assert len(audit.conflict_pairs) == 1
    assert "DRUG_A + DRUG_B" in caplog.text or "drug_a + drug_b" in caplog.text
    assert len(audit.unlabeled_pairs) == 1
    assert audit.unlabeled_pairs.iloc[0]["severity"] == "Unknown"
    assert "Unknown" not in set(audit.labeled_pairs["severity"])
    assert audit.whitelist_present == ("DRUG_A", "DRUG_B")


def test_cold_drug_split_has_zero_test_drug_overlap_with_training_edges():
    split = cold_drug_split(_edge_table())
    train_drugs = set(split.train["drug_a"]) | set(split.train["drug_b"])
    assert split.test_drugs.isdisjoint(split.train_drugs)
    assert split.test_drugs.isdisjoint(train_drugs)
    assert not split.train.empty and not split.validation.empty and not split.test.empty


def test_random_pair_split_is_seeded_and_stratifies_when_possible():
    edges = _edge_table()
    first = make_splits(edges)["RANDOM_PAIR"]
    second = make_splits(edges)["RANDOM_PAIR"]
    assert first.stratified
    assert first.train.equals(second.train)
    assert first.validation.equals(second.validation)
    assert first.test.equals(second.test)


def test_test_edge_label_change_cannot_change_train_graph_features():
    edges = _edge_table()
    split = cold_drug_split(edges)
    before = fit_drug_vectors(split.train)
    changed_test = split.test.copy()
    changed_test.loc[changed_test.index[0], "severity"] = "Major"
    after = fit_drug_vectors(split.train)
    assert before.vectors.keys() == after.vectors.keys()
    assert all(np.array_equal(before.vectors[key], after.vectors[key]) for key in before.vectors)


def test_pair_features_are_symmetric():
    vectors = fit_drug_vectors(_edge_table())
    assert np.array_equal(pair_features("drug_01", "drug_07", vectors),
                          pair_features("drug_07", "drug_01", vectors))


def test_unseen_drug_gets_zero_vector_and_symmetric_flag():
    vectors = fit_drug_vectors(_edge_table())
    value, unseen = vectors.get("UNKNOWN_DRUG")
    assert unseen and np.count_nonzero(value) == 0
    feature = pair_features("drug_01", "UNKNOWN_DRUG", vectors)
    assert feature[-1] == 1


def test_seeded_training_runs_give_identical_predictions():
    x = np.asarray([[i, i % 3, (i * 7) % 5] for i in range(90)], dtype=float)
    y = np.asarray([("Major", "Moderate", "Minor")[i % 3] for i in range(90)])
    first = make_classifier("logistic_regression").fit(x, y)
    second = make_classifier("logistic_regression").fit(x, y)
    assert np.array_equal(first.predict(x), second.predict(x))
    assert np.array_equal(first.predict_proba(x), second.predict_proba(x))


def test_validation_tau_requires_accuracy_coverage_and_major_precision():
    probabilities = np.asarray([
        [0.95, 0.03, 0.02], [0.90, 0.06, 0.04], [0.05, 0.85, 0.10],
        [0.05, 0.15, 0.80], [0.75, 0.20, 0.05], [0.10, 0.70, 0.20],
        [0.10, 0.25, 0.65], [0.05, 0.60, 0.35], [0.40, 0.05, 0.55],
        [0.50, 0.30, 0.20],
    ])
    y_true = np.asarray([
        "Major", "Major", "Moderate", "Minor", "Moderate", "Minor",
        "Minor", "Moderate", "Major", "Minor",
    ])
    assert choose_tau(y_true, probabilities) == pytest.approx(0.80)
    no_qualifying_probabilities = np.tile(np.asarray([[0.5, 0.3, 0.2]]), (10, 1))
    assert choose_tau(np.asarray(["Moderate"] * 10), no_qualifying_probabilities) == 1.01


class _FixedClassifier:
    classes_ = np.asarray(["Major", "Moderate", "Minor"])

    def predict_proba(self, matrix):
        return np.tile(np.asarray([[0.60, 0.25, 0.15]]), (len(matrix), 1))


def test_predictor_abstains_below_tau_and_returns_prediction_above_tau(monkeypatch):
    from medsafe.ml import predict

    vectors = DrugVectors({"drug_a": np.zeros(20), "drug_b": np.zeros(20)}, 20)
    monkeypatch.setattr(predict, "load_model", lambda: predict.LoadedModel(
        _FixedClassifier(), vectors, 0.70, True, frozenset({("drug_a", "drug_b")} ),
        frozenset({("drug_a", "drug_b")})))
    assert predict.predict_pair("DRUG_A", "DRUG_B") is None
    monkeypatch.setattr(predict, "load_model", lambda: predict.LoadedModel(
        _FixedClassifier(), vectors, 0.50, True, frozenset({("drug_a", "drug_b")} ),
        frozenset({("drug_a", "drug_b")})))
    assert predict.predict_pair("DRUG_A", "DRUG_B") == ("Major", 0.60)
    assert predict.predict_pair("UNKNOWN_DRUG", "DRUG_B") is None
    assert predict.predict_pair("DRUG_A", "DRUG_A") is None


def test_predictor_never_annotates_pair_with_existing_ddinter_severity(monkeypatch):
    from medsafe.ml import predict

    vectors = DrugVectors({"drug_a": np.zeros(20), "drug_b": np.zeros(20)}, 20)
    monkeypatch.setattr(predict, "load_model", lambda: predict.LoadedModel(
        _FixedClassifier(), vectors, 0.50, True,
        frozenset({("drug_a", "drug_b")}), frozenset()))
    assert predict.predict_pair("DRUG_A", "DRUG_B") is None


def test_gate_disabled_returns_none_for_every_pair(monkeypatch):
    from medsafe.ml import predict

    vectors = DrugVectors({"drug_a": np.zeros(20), "drug_b": np.zeros(20)}, 20)
    monkeypatch.setattr(predict, "load_model", lambda: predict.LoadedModel(
        _FixedClassifier(), vectors, 0.0, False, frozenset({("drug_a", "drug_b")} ),
        frozenset({("drug_a", "drug_b")})))
    assert predict.predict_pair("DRUG_A", "DRUG_B") is None
    assert predict.predict_pair("UNKNOWN", "DRUG_A") is None


def test_tampered_model_file_fails_sha256_verification(tmp_path, monkeypatch):
    from medsafe.ml import predict
    from medsafe.ml.predict import _hash

    model_file = tmp_path / "severity_model.joblib"
    index_file = tmp_path / "drug_index.json"
    model_file.write_bytes(b"before")
    index_file.write_text(json.dumps({"vector_size": 20, "drugs": {}}), encoding="utf-8")
    manifest = {"files": {model_file.name: {"sha256": _hash(model_file)},
                          index_file.name: {"sha256": _hash(index_file)}}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    model_file.write_bytes(b"tampered")
    monkeypatch.setattr(predict, "MODEL_DIR", tmp_path)
    with pytest.raises(ValueError, match="SHA-256 mismatch for severity_model.joblib"):
        predict.load_model()


def test_api_import_does_not_import_optional_ml_package():
    code = "import sys; import medsafe.api.app; assert 'medsafe.ml' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).parents[1])
