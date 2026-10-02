"""Load, canonicalize, deduplicate, and audit local DDInter CSVs."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from medsafe.ml.config import SEVERITIES, SEVERITY_ORDER

RAW_DIR = Path(__file__).resolve().parents[2] / "data/raw/ddinter"
WHITELIST_PATH = Path(__file__).resolve().parents[2] / "data/seed/drug_whitelist.csv"
FILES = tuple(f"ddinter_downloads_code_{letter}.csv" for letter in "ABDH LPRV".replace(" ", ""))
LABEL_MAP = {"major": "Major", "moderate": "Moderate", "minor": "Minor", "unknown": "Unknown"}


@dataclass(frozen=True)
class DataAudit:
    total_rows_read: int
    raw_label_counts: dict[str, int]
    unique_pairs: pd.DataFrame
    labeled_pairs: pd.DataFrame
    unlabeled_pairs: pd.DataFrame
    unique_drugs: tuple[str, ...]
    conflict_pairs: tuple[dict[str, str], ...]
    whitelist_present: tuple[str, ...]
    unknown_share: float
    unknown_labels: tuple[str, ...]
    demo_raw_unknown_share: float = 0.0


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a.strip(), b.strip()), key=str.casefold))  # type: ignore[return-value]


def load_ddinter(raw_dir: Path = RAW_DIR, whitelist_path: Path = WHITELIST_PATH) -> DataAudit:
    frames: list[pd.DataFrame] = []
    rows_read = 0
    for filename in FILES:
        path = raw_dir / filename
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        expected = {"Drug_A", "Drug_B", "Level"}
        missing = expected - set(frame.columns)
        if missing:
            raise ValueError(f"{filename} missing columns: {sorted(missing)}")
        rows_read += len(frame)
        frames.append(frame[["Drug_A", "Drug_B", "Level"]].rename(columns={
            "Drug_A": "drug_a", "Drug_B": "drug_b", "Level": "raw_severity"}))
    raw = pd.concat(frames, ignore_index=True)
    raw["drug_a"] = raw["drug_a"].str.strip().str.casefold()
    raw["drug_b"] = raw["drug_b"].str.strip().str.casefold()
    raw["raw_severity"] = raw["raw_severity"].str.strip()
    raw_label_counts = raw["raw_severity"].value_counts(dropna=False).sort_index().to_dict()
    mapped = raw["raw_severity"].str.casefold().map(LABEL_MAP)
    unknown_labels = tuple(sorted(raw.loc[mapped.isna(), "raw_severity"].unique()))
    if unknown_labels:
        raise ValueError(f"Unmapped DDInter labels: {unknown_labels}")
    raw["severity"] = mapped
    first_before_second = raw["drug_a"].le(raw["drug_b"])
    left = raw["drug_a"].where(first_before_second, raw["drug_b"])
    right = raw["drug_b"].where(first_before_second, raw["drug_a"])
    raw["drug_a"], raw["drug_b"] = left, right
    rank_map = {"Major": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}
    raw["_rank"] = raw["severity"].map(rank_map)
    groups = raw.groupby(["drug_a", "drug_b"], sort=True, dropna=False)
    conflict_keys = groups["severity"].nunique()
    conflict_keys = conflict_keys[conflict_keys > 1].index
    conflict_frame = raw.set_index(["drug_a", "drug_b"]).loc[conflict_keys].reset_index()
    label_lists = conflict_frame.groupby(["drug_a", "drug_b"], sort=True)["severity"].agg(
        lambda values: tuple(sorted(set(values), key=lambda label: -rank_map[label])))
    unique_pairs = (raw.sort_values(["_rank"], ascending=False)
        .drop_duplicates(["drug_a", "drug_b"])[["drug_a", "drug_b", "severity"]]
        .sort_values(["drug_a", "drug_b"], kind="stable").reset_index(drop=True))
    final_severity = unique_pairs.set_index(["drug_a", "drug_b"])["severity"]
    conflicts: list[dict[str, str]] = []
    for (drug_a, drug_b), labels in label_lists.items():
        chosen = final_severity.loc[(drug_a, drug_b)]
        item = {"drug_a": drug_a, "drug_b": drug_b, "labels": ", ".join(labels),
                "severity": chosen}
        conflicts.append(item)
        logging.warning("Conflicting DDInter duplicate pair %s + %s labels=%s kept=%s",
                        drug_a, drug_b, item["labels"], chosen)
    unlabeled = unique_pairs.loc[unique_pairs["severity"].eq("Unknown")].reset_index(drop=True)
    labeled = unique_pairs.loc[unique_pairs["severity"].isin(SEVERITIES)].reset_index(drop=True)
    all_drugs = tuple(sorted(set(raw["drug_a"]) | set(raw["drug_b"]), key=str.casefold))
    whitelist = tuple(line.strip() for line in whitelist_path.read_text(encoding="utf-8-sig").splitlines()
                      if line.strip() and not line.lstrip().startswith("#"))
    present_set = {drug.casefold() for drug in all_drugs}
    whitelist_present = tuple(drug for drug in whitelist if drug.casefold() in present_set)
    whitelist_set = {drug.casefold() for drug in whitelist}
    demo_rows = raw.loc[raw["drug_a"].isin(whitelist_set) & raw["drug_b"].isin(whitelist_set)]
    demo_raw_unknown_share = (float(demo_rows["severity"].eq("Unknown").mean())
                              if len(demo_rows) else 0.0)
    unknown_share = len(unlabeled) / len(unique_pairs) if len(unique_pairs) else 0.0
    return DataAudit(rows_read, {str(k): int(v) for k, v in raw_label_counts.items()},
        unique_pairs, labeled, unlabeled, all_drugs, tuple(conflicts), whitelist_present,
        unknown_share, unknown_labels, demo_raw_unknown_share)


def render_data_audit(audit: DataAudit) -> str:
    unique_counts = audit.unique_pairs["severity"].value_counts().to_dict()
    lines = ["# DDInter full-graph data audit", "",
        "Source: local DDInter CSV files in `data/raw/ddinter/`; no network access used.",
        "Pairs are canonicalized by case-insensitive drug name. Duplicate pairs retain highest listed severity.", "",
        "## Counts", "", f"- Total rows read: {audit.total_rows_read:,}",
        f"- Unique canonical pairs: {len(audit.unique_pairs):,}",
        f"- Unique drugs: {len(audit.unique_drugs):,}",
        f"- Unique labeled pairs: {len(audit.labeled_pairs):,}",
        f"- Unknown share of unique pairs: {audit.unknown_share:.2%}",
        f"- Whitelist drugs present: {len(audit.whitelist_present)}/30", "",
        "## Raw rows by label", "", "| Raw label | Rows |", "|---|---:|"]
    lines.extend(f"| {label} | {count:,} |" for label, count in sorted(audit.raw_label_counts.items()))
    lines += ["", "## Deduplicated unique pairs by label", "", "| Label | Pairs |", "|---|---:|"]
    lines.extend(f"| {label} | {int(unique_counts.get(label, 0)):,} |"
                 for label in ("Major", "Moderate", "Minor", "Unknown"))
    lines += ["", f"## Duplicate severity conflicts: {len(audit.conflict_pairs):,}", "",
        "Every conflicting pair was logged during loading. First 10 examples:", "",
        "| Drug A | Drug B | Labels seen | Kept |", "|---|---|---|---|"]
    lines.extend(f"| {p['drug_a']} | {p['drug_b']} | {p['labels']} | {p['severity']} |"
                 for p in audit.conflict_pairs[:10])
    lines += ["", "## Whitelist drugs found", "", ", ".join(audit.whitelist_present), ""]
    return "\n".join(lines)
