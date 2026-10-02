"""Export DDInter MAJOR rules for documented manual review."""
import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["rule_id", "drug_a", "drug_b", "source_url", "mechanism", "recommendation", "reviewer", "verified_on"]


def export_review_sheet(rules_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rules_path.open(encoding="utf-8-sig", newline="") as source:
        rules = csv.DictReader(source)
        selected = [row for row in rules if row.get("severity", "").upper() == "MAJOR"]
    with output_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        for rule in selected:
            drugs = rule.get("drugs", "").split("|")
            if len(drugs) != 2:
                continue
            writer.writerow({"rule_id": rule["rule_id"], "drug_a": drugs[0], "drug_b": drugs[1],
                "source_url": rule.get("source_url", ""), "mechanism": "", "recommendation": "",
                "reviewer": "", "verified_on": ""})
    return len(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, default=ROOT / "data/seed/rules.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/review/major_rules_review.csv")
    args = parser.parse_args()
    print(f"Exported {export_review_sheet(args.rules, args.output)} MAJOR rules to {args.output}")


if __name__ == "__main__":
    main()
