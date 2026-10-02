"""Symmetric pair features fit strictly from training edges."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from sklearn.decomposition import TruncatedSVD

from medsafe.ml.config import EMBEDDING_DIMS, SEED, SEVERITIES


@dataclass(frozen=True)
class DrugVectors:
    vectors: dict[str, np.ndarray]
    vector_size: int

    def get(self, drug: str) -> tuple[np.ndarray, bool]:
        vector = self.vectors.get(drug.casefold())
        if vector is None:
            return np.zeros(self.vector_size, dtype=np.float64), True
        return vector, False


def fit_drug_vectors(train_edges: pd.DataFrame, n_components: int = EMBEDDING_DIMS,
                     seed: int = SEED) -> DrugVectors:
    """Fit every graph statistic and embedding from train_edges only."""
    drugs = sorted(set(train_edges["drug_a"]) | set(train_edges["drug_b"]))
    if not drugs:
        return DrugVectors({}, 4 + n_components)
    index = {drug: i for i, drug in enumerate(drugs)}
    degree = np.zeros(len(drugs), dtype=np.float64)
    label_counts = np.zeros((len(drugs), len(SEVERITIES)), dtype=np.float64)
    rows: list[int] = []
    cols: list[int] = []
    weights: list[float] = []
    severity_weight = {"Major": 3.0, "Moderate": 2.0, "Minor": 1.0}
    for edge in train_edges.itertuples(index=False):
        ia, ib = index[edge.drug_a], index[edge.drug_b]
        class_index = SEVERITIES.index(edge.severity)
        degree[ia] += 1
        label_counts[ia, class_index] += 1
        if ib != ia:
            degree[ib] += 1
            label_counts[ib, class_index] += 1
        rows.append(ia); cols.append(ib); weights.append(severity_weight[edge.severity])
        if ia != ib:
            rows.append(ib); cols.append(ia); weights.append(severity_weight[edge.severity])
    adjacency = coo_matrix((weights, (rows, cols)), shape=(len(drugs), len(drugs))).tocsr()
    components = min(n_components, max(0, len(drugs) - 1))
    embedding = np.zeros((len(drugs), n_components), dtype=np.float64)
    if components:
        svd = TruncatedSVD(n_components=components, random_state=seed)
        embedding[:, :components] = svd.fit_transform(adjacency)
    fractions = np.divide(label_counts, degree[:, None], out=np.zeros_like(label_counts),
                          where=degree[:, None] > 0)
    combined = np.column_stack((degree, fractions, embedding))
    return DrugVectors({drug: combined[index[drug]] for drug in drugs}, combined.shape[1])


def pair_features(drug_a: str, drug_b: str, features: DrugVectors) -> np.ndarray:
    a, unseen_a = features.get(drug_a)
    b, unseen_b = features.get(drug_b)
    degree_a, degree_b = a[0], b[0]
    return np.concatenate((a + b, np.abs(a - b), a * b,
                           np.array([min(degree_a, degree_b), max(degree_a, degree_b),
                                     float(unseen_a) + float(unseen_b)])))


def pair_matrix(pairs: pd.DataFrame, features: DrugVectors) -> np.ndarray:
    if pairs.empty:
        return np.empty((0, features.vector_size * 3 + 3), dtype=np.float64)
    return np.vstack([pair_features(row.drug_a, row.drug_b, features)
                      for row in pairs.itertuples(index=False)])
