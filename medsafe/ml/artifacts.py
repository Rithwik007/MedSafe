"""Local checksum-verified model artifact writing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from medsafe.ml.features import DrugVectors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_edges(edges) -> str:
    rows = edges[["drug_a", "drug_b", "severity"]].sort_values(
        ["drug_a", "drug_b", "severity"], kind="stable")
    payload = rows.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_artifacts(model_dir: Path, classifier: Any, vectors: DrugVectors,
                    manifest_values: dict[str, Any],
                    listed_pairs: list[tuple[str, str]],
                    unlabeled_pairs: list[tuple[str, str]]) -> dict[str, Any]:
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "severity_model.joblib"
    index_path = model_dir / "drug_index.json"
    joblib.dump(classifier, model_path, compress=3)
    index_data = {"feature_version": 1, "vector_size": vectors.vector_size,
        "vector_columns": ["degree", "major_fraction", "moderate_fraction", "minor_fraction"]
            + [f"svd_{i + 1}" for i in range(vectors.vector_size - 4)],
        "drugs": {drug: vector.tolist() for drug, vector in sorted(vectors.vectors.items())},
        "listed_pairs": [list(pair) for pair in sorted({
            tuple(sorted((left.casefold(), right.casefold()))) for left, right in listed_pairs})],
        "unlabeled_pairs": [list(pair) for pair in sorted({
            tuple(sorted((left.casefold(), right.casefold()))) for left, right in unlabeled_pairs})]}
    index_path.write_text(json.dumps(index_data, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")), encoding="utf-8")
    manifest = {**manifest_values, "files": {
        model_path.name: {"sha256": sha256_file(model_path)},
        index_path.name: {"sha256": sha256_file(index_path)},
    }}
    manifest_path = model_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest
