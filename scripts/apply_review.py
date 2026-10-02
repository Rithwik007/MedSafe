"""Apply only complete, source-backed manual review rows to rules.csv."""
import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_REVIEW_FIELDS = ("source_url", "mechanism", "recommendation", "reviewer", "verified_on")


def apply_review(rules_path: Path, sheet_path: Path) -> int:
    with rules_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        rules = list(reader)
    by_id = {row["rule_id"]: row for row in rules}
    applied = 0
    with sheet_path.open(encoding="utf-8-sig", newline="") as stream:
        for review in csv.DictReader(stream):
            target = by_id.get((review.get("rule_id") or "").strip())
            if not target or target.get("severity", "").upper() != "MAJOR":
                continue
            if any(not (review.get(field) or "").strip() for field in REQUIRED_REVIEW_FIELDS):
                continue
            for field in ("source_url", "mechanism", "recommendation", "verified_on"):
                target[field] = review[field].strip()
            target["reviewed_by"] = review["reviewer"].strip()
            target["review_status"] = "reviewed"
            applied += 1
    temporary = rules_path.with_suffix(rules_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rules)
    temporary.replace(rules_path)
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, default=ROOT / "data/seed/rules.csv")
    parser.add_argument("--sheet", type=Path, default=ROOT / "data/review/major_rules_review.csv")
    args = parser.parse_args()
    print(f"Applied {apply_review(args.rules, args.sheet)} completed MAJOR reviews")


if __name__ == "__main__":
    main()
