"""Train, evaluate, gate, and save the offline DDInter severity prototype."""
from __future__ import annotations

import hashlib
import json
import logging
from importlib.metadata import version
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from medsafe.ml.artifacts import sha256_edges, write_artifacts
from medsafe.ml.config import GATE_MACRO_F1_MARGIN, GATE_MAJOR_RECALL_MIN, SEED
from medsafe.ml.data import RAW_DIR, DataAudit, load_ddinter, render_data_audit
from medsafe.ml.features import pair_features
from medsafe.ml.predict import load_model, predict_pair
from medsafe.ml.reporting import render_evaluation, render_model_card
from medsafe.ml.splits import make_splits
from medsafe.ml.training import PreparedExperiment, evaluate_test_once, prepare_experiment

REPORTS = ROOT / "reports"
MODEL_DIR = ROOT / "models"


def _raw_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(RAW_DIR.glob("*.csv"), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8")); digest.update(b"\0")
        digest.update(path.read_bytes()); digest.update(b"\0")
    return digest.hexdigest()


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _test_metrics(audit: DataAudit,
                  experiments: dict[str, PreparedExperiment]) -> tuple[dict, dict, list[str]]:
    whitelist = {drug.casefold() for drug in audit.whitelist_present}
    results: dict[str, dict] = {}
    counts: dict[str, int] = {}
    touch_lines: list[str] = []
    for name, experiment in experiments.items():
        result = evaluate_test_once(experiment, whitelist, touch_lines)
        results[name] = result
        test_pairs = experiment.split.test
        counts[name] = int((test_pairs["drug_a"].str.casefold().isin(whitelist)
            | test_pairs["drug_b"].str.casefold().isin(whitelist)).sum())
    if len(touch_lines) != 2:
        raise AssertionError(f"Expected exactly two test-split touches, got {len(touch_lines)}")
    return results, counts, touch_lines


def _gate(results: dict[str, dict[str, dict]], experiments: dict[str, PreparedExperiment]) -> dict:
    random = results["RANDOM_PAIR"]
    selected = experiments["RANDOM_PAIR"].chosen_name
    model_metric = random[selected]["all"]
    baseline_metrics = [random[f"baseline:{name}"]["all"]
                        for name in experiments["RANDOM_PAIR"].baseline_names]
    best_baseline = max(metric["macro_f1"] for metric in baseline_metrics)
    enabled = (model_metric["macro_f1"] >= best_baseline + GATE_MACRO_F1_MARGIN
               and model_metric["major_recall"] >= GATE_MAJOR_RECALL_MIN)
    return {"enabled": bool(enabled),
        "criterion": "RANDOM_PAIR test macro-F1 >= best baseline + fixed margin AND Major recall >= fixed minimum",
        "fixed_thresholds": {"macro_f1_margin": GATE_MACRO_F1_MARGIN,
                             "major_recall_min": GATE_MAJOR_RECALL_MIN},
        "random_pair_test": {"model_name": selected,
            "model_macro_f1": model_metric["macro_f1"],
            "best_baseline_macro_f1": best_baseline,
            "major_recall": model_metric["major_recall"],
            "macro_f1_condition_passed": model_metric["macro_f1"] >= best_baseline + GATE_MACRO_F1_MARGIN,
            "major_recall_condition_passed": model_metric["major_recall"] >= GATE_MAJOR_RECALL_MIN},
        "cold_drug_affects_gate": False}


def _examples(audit: DataAudit, gate: dict, experiment: PreparedExperiment) -> list[str]:
    names = sorted(experiment.drug_vectors.vectors)
    if len(names) < 2:
        return ["No indexed pair available for examples."]
    loaded = load_model()
    known_pairs = [pair for pair in sorted(loaded.unlabeled_pairs)
                   if pair[0] in experiment.drug_vectors.vectors
                   and pair[1] in experiment.drug_vectors.vectors]
    pairs: list[tuple[str, str]] = known_pairs[:3]
    abstain_pair = None
    if loaded.enabled:
        for pair in known_pairs:
            matrix = pair_features(*pair, loaded.vectors).reshape(1, -1)
            probability = float(np.max(loaded.classifier.predict_proba(matrix)[0]))
            if probability < loaded.tau and pair not in pairs:
                abstain_pair = pair
                break
    if abstain_pair and abstain_pair not in pairs:
        pairs.append(abstain_pair)
    unknown_pair = next((pair for pair in sorted(loaded.unlabeled_pairs)
        if ((pair[0] not in experiment.drug_vectors.vectors)
            != (pair[1] not in experiment.drug_vectors.vectors))), None)
    if unknown_pair and unknown_pair not in pairs:
        pairs.append(unknown_pair)
    for pair in known_pairs:
        if len(pairs) >= 5:
            break
        if pair not in pairs:
            pairs.append(pair)
    output = []
    for left, right in pairs[:5]:
        prediction = predict_pair(left, right)
        if prediction is None:
            if left.casefold() not in experiment.drug_vectors.vectors or right.casefold() not in experiment.drug_vectors.vectors:
                reason = "unknown to trained drug index"
            elif gate["enabled"]:
                if (left, right) not in loaded.listed_pairs:
                    reason = "pair not listed by DDInter"
                elif (left, right) not in loaded.unlabeled_pairs:
                    reason = "DDInter already provides a severity label"
                else:
                    reason = "abstained below validation-frozen τ" if loaded.enabled else "gate disabled"
            else:
                reason = "gate disabled"
            output.append(f"predict_pair({left!r}, {right!r}) -> None ({reason})")
        else:
            output.append(f"predict_pair({left!r}, {right!r}) -> ML-PREDICTED {prediction[0]} ({prediction[1]:.6f})")
    return output


def run() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    REPORTS.mkdir(parents=True, exist_ok=True)
    conflict_log = REPORTS / "ddinter_conflicts.log"
    logging.basicConfig(filename=conflict_log, level=logging.WARNING, force=True)
    audit = load_ddinter()
    audit_text = render_data_audit(audit)
    (REPORTS / "ml_data_audit.md").write_text(audit_text, encoding="utf-8")
    print(audit_text)
    if len(audit.labeled_pairs) < 2000:
        print(f"STOP: only {len(audit.labeled_pairs)} unique labeled pairs; minimum is 2000.")
        return 2
    raw_fingerprint = _raw_fingerprint()

    splits = make_splits(audit.labeled_pairs, SEED)
    experiments = {name: prepare_experiment(name, split, SEED)
                   for name, split in splits.items()}
    results, whitelist_counts, touch_lines = _test_metrics(audit, experiments)
    gate = _gate(results, experiments)
    _write_json(REPORTS / "ml_gate.json", gate)
    eval_text = render_evaluation(experiments, results, whitelist_counts, touch_lines, gate)
    (REPORTS / "ml_eval.md").write_text(eval_text, encoding="utf-8")
    (REPORTS / "ml_test_split.log").write_text("\n".join(touch_lines) + "\n", encoding="utf-8")

    random_experiment = experiments["RANDOM_PAIR"]
    train_fingerprint = sha256_edges(random_experiment.split.train)
    manifest_values = {"model_name": random_experiment.chosen_name,
        "training_split": "RANDOM_PAIR train only", "training_data_fingerprint": train_fingerprint,
        "raw_source_fingerprint": raw_fingerprint, "seed": SEED,
        "tau": random_experiment.tau, "gate": gate,
        "listed_pair_count": len(audit.unique_pairs),
        "unlabeled_pair_count": len(audit.unlabeled_pairs),
        "versions": {package: version(package) for package in
                     ("scikit-learn", "numpy", "scipy", "pandas", "joblib")}}
    manifest = write_artifacts(MODEL_DIR, random_experiment.chosen_model,
        random_experiment.drug_vectors, manifest_values,
        list(audit.unique_pairs[["drug_a", "drug_b"]].itertuples(index=False, name=None)),
        list(audit.unlabeled_pairs[["drug_a", "drug_b"]].itertuples(index=False, name=None)))
    model_card = render_model_card(audit, gate, eval_text,
        random_experiment.chosen_name, random_experiment.tau, results)
    (REPORTS / "ml_model_card.md").write_text(model_card, encoding="utf-8")

    print("\n=== FULL EVALUATION REPORT ===\n")
    print(eval_text)
    print("\n=== GATE JSON ===")
    print(json.dumps(gate, indent=2, sort_keys=True))
    print("\n=== MODEL MANIFEST ===")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("\n=== FIVE PREDICTOR EXAMPLES ===")
    for line in _examples(audit, gate, random_experiment):
        print(line)
    print("\n=== TEST-SPLIT TOUCH LOG ===")
    print((REPORTS / "ml_test_split.log").read_text(encoding="utf-8"), end="")
    print("\n=== MODEL CARD ===\n")
    print(model_card)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
