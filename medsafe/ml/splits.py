"""Reproducible pair-random and drug-cold train/validation/test splits."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from medsafe.ml.config import SEED, SEVERITY_ORDER


@dataclass(frozen=True)
class DataSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    train_drugs: frozenset[str]
    validation_drugs: frozenset[str]
    test_drugs: frozenset[str]
    stratified: bool


def _pair_split(edges: pd.DataFrame, seed: int) -> DataSplit:
    stratify = edges["severity"]
    try:
        train, held = train_test_split(edges, test_size=0.30, random_state=seed,
                                       stratify=stratify)
        val, test = train_test_split(held, test_size=0.50, random_state=seed + 1,
                                     stratify=held["severity"])
        stratified = True
    except ValueError:
        train, held = train_test_split(edges, test_size=0.30, random_state=seed)
        val, test = train_test_split(held, test_size=0.50, random_state=seed + 1)
        stratified = False
    def drugs(frame: pd.DataFrame) -> frozenset[str]:
        return frozenset(frame["drug_a"]) | frozenset(frame["drug_b"])
    return DataSplit(train.reset_index(drop=True), val.reset_index(drop=True),
        test.reset_index(drop=True), drugs(train), drugs(val), drugs(test), stratified)


def _dominant_severity(edges: pd.DataFrame, drugs: list[str]) -> list[str]:
    ranks = {label: index for index, label in enumerate(SEVERITY_ORDER)}
    counts: dict[str, dict[str, int]] = {drug: {} for drug in drugs}
    for row in edges.itertuples(index=False):
        for drug in {row.drug_a, row.drug_b}:
            counts.setdefault(drug, {})[row.severity] = counts.setdefault(drug, {}).get(row.severity, 0) + 1
    return [min(counts[drug], key=lambda label: (-counts[drug][label], ranks[label]))
            for drug in drugs]


def _stratified_drug_split(drugs: list[str], labels: list[str], test_size: float,
                           seed: int) -> tuple[list[str], list[str], bool]:
    try:
        left, right = train_test_split(drugs, test_size=test_size, random_state=seed,
                                       stratify=labels)
        return list(left), list(right), True
    except ValueError:
        left, right = train_test_split(drugs, test_size=test_size, random_state=seed)
        return list(left), list(right), False


def cold_drug_split(edges: pd.DataFrame, seed: int = SEED) -> DataSplit:
    drugs = sorted(set(edges["drug_a"]) | set(edges["drug_b"]))
    dominant = _dominant_severity(edges, drugs)
    train_drugs, held_drugs, first_stratified = _stratified_drug_split(
        drugs, dominant, 0.30, seed)
    held_labels = _dominant_severity(edges, held_drugs)
    validation_drugs, test_drugs, second_stratified = _stratified_drug_split(
        held_drugs, held_labels, 0.50, seed + 1)
    train_set, val_set, test_set = map(set, (train_drugs, validation_drugs, test_drugs))
    a, b = edges["drug_a"], edges["drug_b"]
    test_mask = a.isin(test_set) | b.isin(test_set)
    val_mask = ~test_mask & (a.isin(val_set) | b.isin(val_set))
    train_mask = ~test_mask & ~val_mask
    train = edges.loc[train_mask].reset_index(drop=True)
    val = edges.loc[val_mask].reset_index(drop=True)
    test = edges.loc[test_mask].reset_index(drop=True)
    train_seen = set(train["drug_a"]) | set(train["drug_b"])
    overlap = train_seen & test_set
    if overlap:
        raise AssertionError(f"Cold test drugs overlap training edges: {sorted(overlap)}")
    if (not train_set.isdisjoint(val_set) or not train_set.isdisjoint(test_set)
            or not val_set.isdisjoint(test_set)):
        raise AssertionError("Cold drug partitions overlap.")
    return DataSplit(train, val, test, frozenset(train_set), frozenset(val_set),
                     frozenset(test_set), first_stratified and second_stratified)


def make_splits(edges: pd.DataFrame, seed: int = SEED) -> dict[str, DataSplit]:
    return {"RANDOM_PAIR": _pair_split(edges, seed), "COLD_DRUG": cold_drug_split(edges, seed)}
