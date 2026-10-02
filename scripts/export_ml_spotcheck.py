from __future__ import annotations
import csv
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from medsafe.checkers.engine import _load_ml_predictor
from medsafe.kb.rules import RULES

SEED = 20260930
QUOTAS = {"Major": 7, "Moderate": 7, "Minor": 6}

def select_balanced_pairs(buckets: dict[str, list[tuple[str, str]]],
                          quotas: dict[str, int] = QUOTAS,
                          per_drug_cap: int = 2, seed: int = SEED):
    rng = random.Random(seed)
    counts: Counter[str] = Counter()
    selected: list[tuple[tuple[str, str], str]] = []
    shortfalls = {}
    for label, quota in quotas.items():
        candidates = sorted(set(tuple(sorted(pair, key=str.casefold))
                                for pair in buckets.get(label, [])),
                            key=lambda pair: tuple(x.casefold() for x in pair))
        rng.shuffle(candidates)
        accepted = []
        for pair in candidates:
            if len(accepted) >= quota:
                break
            if any(counts[drug.casefold()] >= per_drug_cap for drug in pair):
                continue
            accepted.append(pair)
            for drug in pair:
                counts[drug.casefold()] += 1
        selected.extend((pair, label) for pair in accepted)
        if len(accepted) < quota:
            shortfalls[label] = quota - len(accepted)
    return selected, dict(counts), shortfalls

def collect_buckets():
    whitelist = {line.strip().casefold() for line in (ROOT / "data/seed/drug_whitelist.csv").read_text(encoding="utf-8-sig").splitlines() if line.strip()}
    predictor = _load_ml_predictor()
    if predictor.state != "ENABLED" or predictor.predict_pair is None:
        raise RuntimeError(f"ML predictor unavailable: {predictor.reason}")
    buckets = {label: [] for label in QUOTAS}
    for rule in RULES:
        if rule.kind.value != "DDI" or rule.severity.value != "UNSPECIFIED" or len(rule.drugs) != 2:
            continue
        pair = tuple(sorted(rule.drugs, key=str.casefold))
        left, right = (drug.casefold() for drug in pair)
        if left not in whitelist or right not in whitelist:
            continue
        result = predictor.predict_pair(left, right)
        if result:
            label = result[0].title()
            if label in buckets:
                buckets[label].append(pair)
    return buckets

def main() -> None:
    buckets = collect_buckets()
    selected, drug_counts, shortfalls = select_balanced_pairs(buckets)
    output = ROOT / "reports/ml_spotcheck.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["pair", "predicted_label", "source_checked", "source_url", "source_result", "agrees", "notes"])
        for pair, label in selected:
            writer.writerow([" + ".join(pair), label, "", "", "", "", ""])
    labels = Counter(label for _, label in selected)
    print(f"Wrote {len(selected)} seeded rows to {output}")
    print(f"Selected labels: {dict(labels)}")
    for label, shortfall in shortfalls.items():
        print(f"SHORTFALL {label}: requested {QUOTAS[label]}, selected {QUOTAS[label]-shortfall}, short by {shortfall}")
    print("Per-drug row counts:")
    for drug, count in sorted(drug_counts.items()):
        print(f"- {drug}: {count}")
    print(f"Cap: at most 2 selected pairs per drug; verified={all(n <= 2 for n in drug_counts.values())}")

if __name__ == "__main__":
    main()

