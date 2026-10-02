"""CSV status reader for checker families that remain unimplemented."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHECKER_COLUMNS = {
    "allergy_rules.csv": ("rule_id", "drug", "allergen", "match_type", "label_category",
        "reason", "recommendation", "source_name", "source_url", "source_section",
        "accessed_on", "reviewed_by", "verified_on"),
    "drug_disease_rules.csv": ("rule_id", "drug", "condition", "label_category", "reason",
        "recommendation", "source_name", "source_url", "source_section", "accessed_on",
        "reviewed_by", "verified_on"),
    "dose_limits.csv": ("rule_id", "drug", "route", "population", "age_min_years",
        "age_max_years", "dose_unit", "max_single_dose", "max_daily_dose", "per_kg_basis",
        "renal_note", "source_name", "source_url", "source_section", "accessed_on",
        "reviewed_by", "verified_on"),
}


def load_checker_rows(filename: str) -> list[dict[str, str]]:
    path = ROOT / "data/seed" / filename
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != CHECKER_COLUMNS[filename]:
            raise ValueError(f"Unexpected columns in {filename}.")
        return list(reader)


def reviewed_rows(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return sum(1 for row in csv.DictReader(stream)
                   if (row.get("reviewed_by") or "").strip()
                   and (row.get("verified_on") or "").strip()
                   and (row.get("source_url") or "").strip())


def stub_status(filename: str) -> tuple[str, str, int]:
    count = sum(1 for row in load_checker_rows(filename)
                if (row.get("reviewed_by") or "").strip()
                and (row.get("verified_on") or "").strip()
                and (row.get("source_url") or "").strip())
    if count == 0:
        return "NOT_RUN_NO_DATA", f"No reviewed rows in {filename}; checker not run.", 0
    return "PARTIAL", "Reviewed rows exist, but checker logic is not implemented.", count
