"""Tally manually completed spot-check sheets without inferring results."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


CATEGORIES = ("agree", "disagree", "unclear", "unfilled", "invalid")
CAVEAT = "Spot check, not validation. n is small. Unclear is not agreement."


def tally_rows(rows: Iterable[dict[str, str | None]]) -> dict:
    overall = {name: [] for name in CATEGORIES}
    by_label: dict[str, dict[str, list[tuple[str, str | None]]]] = {}
    row_count = 0
    for row in rows:
        row_count += 1
        pair = (row.get("pair") or "").strip() or "(missing pair)"
        label = (row.get("predicted_label") or "").strip() or "(missing label)"
        value = (row.get("agrees") or "").strip().casefold()
        category = value if value in {"agree", "disagree", "unclear"} else (
            "unfilled" if not value else "invalid")
        invalid_value = (row.get("agrees") or "").strip() if category == "invalid" else None
        overall[category].append((pair, invalid_value))
        by_label.setdefault(label, {name: [] for name in CATEGORIES})[category].append(
            (pair, invalid_value))
    return {"row_count": row_count, "overall": overall, "by_predicted_label": by_label}


def tally_csv(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            return tally_rows(())
        missing = {"pair", "predicted_label", "agrees"} - set(reader.fieldnames)
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
        return tally_rows(reader)


def _print_bucket(name: str, pairs: list[tuple[str, str | None]], indent: str) -> list[str]:
    lines = [f"{indent}{name}: {len(pairs)}", f"{indent}  pairs:"]
    if pairs:
        lines.extend(f"{indent}    - {pair}" +
                     (f" [invalid agrees={value!r}]" if value is not None else "")
                     for pair, value in pairs)
    else:
        lines.append(f"{indent}    - (none)")
    return lines


def render_tally(result: dict) -> str:
    lines = [f"Input rows: {result['row_count']}", "Overall:"]
    for category in CATEGORIES:
        lines.extend(_print_bucket(category, result["overall"][category], "  "))
    lines.append("By predicted_label:")
    if not result["by_predicted_label"]:
        lines.append("  (none)")
    for label in sorted(result["by_predicted_label"], key=str.casefold):
        lines.append(f"  {label}:")
        for category in CATEGORIES:
            lines.extend(_print_bucket(category,
                result["by_predicted_label"][label][category], "    "))
    lines.extend((CAVEAT, ""))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Completed or in-progress spot-check CSV")
    args = parser.parse_args()
    print(render_tally(tally_csv(args.csv_path)), end="")


if __name__ == "__main__":
    main()
