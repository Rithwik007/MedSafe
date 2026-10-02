"""Load and predict locally from a checksum-verified severity artifact."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from medsafe.ml.features import DrugVectors, pair_features

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


@dataclass(frozen=True)
class LoadedModel:
    classifier: Any
    vectors: DrugVectors
    tau: float
    enabled: bool
    listed_pairs: frozenset[tuple[str, str]] = frozenset()
    unlabeled_pairs: frozenset[tuple[str, str]] = frozenset()


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model() -> LoadedModel:
    manifest_path = MODEL_DIR / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read local model manifest: {error}") from error
    for filename, details in manifest.get("files", {}).items():
        artifact = (MODEL_DIR / filename).resolve()
        if artifact.parent != MODEL_DIR.resolve():
            raise ValueError(f"Invalid model artifact path: {filename}")
        if not artifact.is_file():
            raise ValueError(f"Missing model artifact: {filename}")
        if _hash(artifact) != details.get("sha256"):
            raise ValueError(f"SHA-256 mismatch for {filename}")
    required = {"severity_model.joblib", "drug_index.json"}
    if not required.issubset(manifest.get("files", {})):
        raise ValueError("Model manifest does not checksum every required artifact.")
    import joblib
    classifier = joblib.load(MODEL_DIR / "severity_model.joblib")
    index_data = json.loads((MODEL_DIR / "drug_index.json").read_text(encoding="utf-8"))
    vectors = {drug.casefold(): np.asarray(vector, dtype=np.float64)
               for drug, vector in index_data["drugs"].items()}
    listed_pairs = frozenset(tuple(sorted((pair[0].casefold(), pair[1].casefold())))
                             for pair in index_data.get("listed_pairs", []))
    unlabeled_pairs = frozenset(tuple(sorted((pair[0].casefold(), pair[1].casefold())))
                                for pair in index_data.get("unlabeled_pairs", []))
    return LoadedModel(classifier, DrugVectors(vectors, int(index_data["vector_size"])),
                       float(manifest["tau"]), bool(manifest["gate"]["enabled"]), listed_pairs,
                       unlabeled_pairs)


def predict_pair(drug_a: str, drug_b: str) -> tuple[str, float] | None:
    loaded = load_model()
    if not loaded.enabled:
        return None
    if drug_a.casefold() not in loaded.vectors.vectors or drug_b.casefold() not in loaded.vectors.vectors:
        return None
    pair = tuple(sorted((drug_a.casefold(), drug_b.casefold())))
    if pair not in loaded.listed_pairs or pair not in loaded.unlabeled_pairs:
        return None
    matrix = pair_features(drug_a, drug_b, loaded.vectors).reshape(1, -1)
    probabilities = loaded.classifier.predict_proba(matrix)[0]
    index = int(np.argmax(probabilities))
    probability = float(probabilities[index])
    if probability < loaded.tau:
        return None
    return str(loaded.classifier.classes_[index]), probability
