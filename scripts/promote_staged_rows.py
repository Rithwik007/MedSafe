"""Promote only staged checker rows with both source-review fields populated."""
from __future__ import annotations

import csv
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "reports" / "b14_staging"
SEED = ROOT / "data" / "seed"
FILES = ("allergy_rules.csv", "drug_disease_rules.csv", "dose_limits.csv")


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def promote(staging: Path = STAGING, filenames: tuple[str, ...] = FILES
            ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    promoted: dict[str, list[str]] = {}
    not_promoted: dict[str, list[str]] = {}
    work: list[tuple[Path, list[str], list[dict[str, str]], list[dict[str, str]]]] = []
    for filename in filenames:
        if filename not in FILES:
            raise ValueError(f"Unsupported staged file: {filename}")
        source, target = staging / filename, SEED / filename
        source_header, source_rows = read_rows(source)
        target_header, target_rows = read_rows(target)
        if source_header != target_header:
            raise ValueError(f"Header mismatch for {filename}; no rows promoted.")
        if "rule_id" not in source_header or "reviewed_by" not in source_header or "verified_on" not in source_header:
            raise ValueError(f"Required promotion fields absent in {filename}; no rows promoted.")
        existing = {row.get("rule_id", "").strip() for row in target_rows if row.get("rule_id", "").strip()}
        duplicates = sorted({row.get("rule_id", "").strip() for row in source_rows
                             if row.get("rule_id", "").strip() in existing})
        if duplicates:
            raise ValueError(f"Target {filename} already contains rule_id(s): {', '.join(duplicates)}")
        ready = [row for row in source_rows
                 if row.get("reviewed_by", "").strip() and row.get("verified_on", "").strip()]
        pending = [row for row in source_rows
                   if not (row.get("reviewed_by", "").strip() and row.get("verified_on", "").strip())]
        promoted[filename] = [row["rule_id"].strip() for row in ready]
        not_promoted[filename] = [row.get("rule_id", "").strip() or f"row {i + 2}"
                                  for i, row in enumerate(source_rows)
                                  if row in pending]
        work.append((target, target_header, target_rows, ready))
    # Run all conflict and schema checks before the first target is written.
    for target, header, old_rows, ready in work:
        if not ready:
            continue
        with target.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(old_rows)
            writer.writerows(ready)
    return promoted, not_promoted


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-dir", type=Path, default=STAGING)
    parser.add_argument("--files", nargs="+", choices=FILES, default=list(FILES))
    args = parser.parse_args()
    promoted, not_promoted = promote(args.staging_dir, tuple(args.files))
    for filename in args.files:
        print(f"{filename}: promoted={promoted[filename]}; not promoted={not_promoted[filename]}")
