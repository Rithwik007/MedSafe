"""Validate source-tracked allergy, disease, and dose CSV rows."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from medsafe.checkers.stubs import CHECKER_COLUMNS
from medsafe.core.normalizer import normalize_drug


@dataclass(frozen=True)
class Issue:
    file: str
    row: int
    column: str
    message: str
    warning: bool = False

DATE_COLUMNS = ("accessed_on", "verified_on")
REQUIRED_COMMON = ("rule_id", "drug", "source_name", "source_url", "source_section", "accessed_on")
SCHEMAS = CHECKER_COLUMNS


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _condition_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    _, rows = _read(path)
    aliases: dict[str, str] = {}
    for row in rows:
        canonical = _norm((row.get("condition_id") or row.get("display_name") or "").strip())
        if not canonical:
            continue
        for field in ("condition_id", "display_name", "synonym"):
            value = (row.get(field) or "").strip()
            if value:
                aliases[_norm(value)] = canonical
    return aliases


def _severity_categories(path: Path) -> set[str]:
    if not path.exists():
        return set()
    _, rows = _read(path)
    return {(row.get("label_category") or "").strip() for row in rows
            if (row.get("label_category") or "").strip()}


def _valid_date(value: str) -> date | None:
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except (TypeError, ValueError):
        return None


def validate(seed_dir: Path, strict: bool = False) -> tuple[list[Issue], dict[str, int]]:
    issues: list[Issue] = []
    counts: dict[str, int] = {}
    categories = _severity_categories(seed_dir / "severity_policy.csv")
    condition_map = _condition_map(seed_dir / "conditions.csv")
    units_path = seed_dir / "units.csv"
    _, unit_rows = _read(units_path) if units_path.exists() else ([], [])
    mass_units = {(row.get("canonical_unit") or "").strip().casefold()
                  for row in unit_rows if (row.get("kind") or "").strip().upper() == "MASS"}

    for filename, expected in SCHEMAS.items():
        path = seed_dir / filename
        if not path.exists():
            issues.append(Issue(filename, 1, "file", "required CSV file is missing"))
            counts[filename] = 0
            continue
        columns, rows = _read(path)
        counts[filename] = len(rows)
        for column in expected:
            if column not in columns:
                issues.append(Issue(filename, 1, column, "required column is missing"))
        for column in columns:
            if column not in expected:
                issues.append(Issue(filename, 1, column, "unknown column"))
        if any(column not in columns for column in expected):
            continue

        seen_ids: set[str] = set()
        seen_keys: set[tuple[str, ...]] = set()
        for row_number, row in enumerate(rows, start=2):
            def error(column: str, message: str, warning: bool = False) -> None:
                issues.append(Issue(filename, row_number, column, message, warning))

            required = list(REQUIRED_COMMON)
            if filename == "allergy_rules.csv":
                required += ["allergen", "reason", "label_category"]
            elif filename == "drug_disease_rules.csv":
                required += ["condition", "reason", "label_category"]
            for column in required:
                if not (row.get(column) or "").strip():
                    error(column, "must not be blank")

            rule_id = (row.get("rule_id") or "").strip()
            if rule_id in seen_ids and rule_id:
                error("rule_id", "duplicate rule_id")
            seen_ids.add(rule_id)

            source_url = (row.get("source_url") or "").strip()
            parsed_url = urlparse(source_url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                error("source_url", "must start with http:// or https://")

            accessed = (row.get("accessed_on") or "").strip()
            verified = (row.get("verified_on") or "").strip()
            accessed_date = _valid_date(accessed) if accessed else None
            verified_date = _valid_date(verified) if verified else None
            for column, value, parsed in (("accessed_on", accessed, accessed_date),
                                          ("verified_on", verified, verified_date)):
                if value and parsed is None:
                    error(column, "must be a valid ISO date")
                elif parsed and parsed > date.today():
                    error(column, "date must not be in the future")
            if accessed_date and verified_date and verified_date < accessed_date:
                error("verified_on", "must be on or after accessed_on")
            reviewer = (row.get("reviewed_by") or "").strip()
            if bool(reviewer) != bool(verified):
                error("verified_on" if reviewer else "reviewed_by",
                      "reviewed_by and verified_on must both be blank or both be set")

            category = (row.get("label_category") or "").strip()
            if filename != "dose_limits.csv" and category not in categories:
                error("label_category", "not present in severity_policy.csv")
            if filename == "allergy_rules.csv" and row.get("match_type", "").strip() not in {
                    "DIRECT", "CROSS_REACTIVITY"}:
                error("match_type", "must be DIRECT or CROSS_REACTIVITY")

            drug = (row.get("drug") or "").strip()
            result = normalize_drug(drug) if drug else None
            exact = result is not None and result.status == "matched" and result.confidence == 100
            if not exact or not result.ingredients:
                error("drug", "must resolve by exact curated match")
            elif filename == "dose_limits.csv" and len(result.ingredients) != 1:
                error("drug", "dose rows require a single-ingredient drug")

            if filename == "drug_disease_rules.csv":
                condition = (row.get("condition") or "").strip()
                if _norm(condition) not in condition_map:
                    error("condition", "condition not in conditions.csv", warning=not strict)

            if filename == "dose_limits.csv":
                for column in ("max_single_dose", "max_daily_dose"):
                    try:
                        value = float(row.get(column, ""))
                        if value <= 0:
                            raise ValueError
                    except (TypeError, ValueError):
                        error(column, "must be a positive number")
                try:
                    if float(row.get("max_daily_dose", "")) < float(row.get("max_single_dose", "")):
                        error("max_daily_dose", "must be greater than or equal to max_single_dose")
                except (TypeError, ValueError):
                    pass
                if (row.get("dose_unit") or "").strip().casefold() not in mass_units:
                    error("dose_unit", "must be a MASS unit from units.csv")
                population = (row.get("population") or "").strip()
                population_folded = population.casefold()
                age_min_text = (row.get("age_min_years") or "").strip()
                age_max_text = (row.get("age_max_years") or "").strip()
                label_adult_without_range = (
                    "adult" in population_folded
                    and "age range not stated by label" in population_folded
                )
                if population != "ADULT" and not label_adult_without_range:
                    error("population", "must equal ADULT")
                if label_adult_without_range and not age_min_text and not age_max_text:
                    pass
                elif label_adult_without_range:
                    error("age_min_years", "age bounds must be blank when the label states no age range")
                else:
                    try:
                        age_min = float(age_min_text)
                        age_max = float(age_max_text)
                        if age_min >= age_max:
                            error("age_min_years", "must be less than age_max_years")
                    except (TypeError, ValueError):
                        error("age_min_years", "age bounds must be numeric")

            identity: tuple[str, ...] | None = None
            if exact and result and result.ingredients:
                drug_key = "|".join(sorted(_norm(ingredient) for ingredient in result.ingredients))
                if filename == "allergy_rules.csv":
                    identity = (drug_key, _norm(row.get("allergen", "")))
                elif filename == "drug_disease_rules.csv":
                    condition_key = condition_map.get(_norm(row.get("condition", "")),
                                                       _norm(row.get("condition", "")))
                    identity = (drug_key, condition_key)
                else:
                    identity = (drug_key, (row.get("population") or "").strip())
            if identity and identity in seen_keys:
                error("drug", "duplicate drug/allergen, drug/condition, or drug/population key")
            if identity:
                seen_keys.add(identity)

    for path in sorted(seed_dir.iterdir()):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            continue
        for row_number, line in enumerate(lines, start=1):
            if "EXAMPLE_ONLY" in line:
                issues.append(Issue(path.name, row_number, "row", "EXAMPLE_ONLY is forbidden in data/seed"))
    return issues, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    issues, counts = validate(ROOT / "data/seed", strict=args.strict)
    errors = [issue for issue in issues if not issue.warning]
    warnings = [issue for issue in issues if issue.warning]
    for issue in issues:
        level = "WARNING" if issue.warning else "ERROR"
        print(f"{level} {issue.file}: row {issue.row}, column {issue.column}: {issue.message}")
    for filename, count in counts.items():
        print(f"{filename}: {count} rows")
    print(f"Summary: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
