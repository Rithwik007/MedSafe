"""Spot-check imported whitelist rules against original downloaded DDInter CSV rows."""
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEVERITY_MAP = {"major": "MAJOR", "moderate": "MODERATE", "minor": "MINOR"}


def main() -> None:
    with (ROOT / "data/seed/rules.csv").open(encoding="utf-8-sig", newline="") as stream:
        rules = list(csv.DictReader(stream))
    source_rows = []
    for path in sorted((ROOT / "data/raw/ddinter").glob("ddinter_downloads_code_*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            source_rows.extend(csv.DictReader(stream))
    source_index = {}
    for row in source_rows:
        ids = tuple(sorted((row.get("DDInterID_A", ""), row.get("DDInterID_B", ""))))
        drugs = tuple(sorted(((row.get("Drug_A") or "").casefold(), (row.get("Drug_B") or "").casefold())))
        source_index.setdefault((ids, drugs, (row.get("Level") or "").casefold()), []).append(row)
    sample = random.Random(42).sample(rules, min(10, len(rules)))
    checks = []
    for rule in sample:
        ids = tuple(sorted(rule["rule_id"].removeprefix("DDINTER-").split("-")))
        drugs = tuple(sorted(x.casefold() for x in rule["drugs"].split("|")))
        level = next((label for label, mapped in SEVERITY_MAP.items() if mapped == rule["severity"]), "")
        found = bool(source_index.get((ids, drugs, level)))
        checks.append({"rule_id": rule["rule_id"], "drugs": rule["drugs"],
            "severity": rule["severity"], "result": "PASS" if found else "FAIL"})
    report = {"source": "original DDInter CSV files downloaded from official download page",
        "method": "random.Random(42), compare imported ID pair, names, and mapped risk level",
        "live_detail_pages_checked": False, "checks": checks,
        "passed": sum(x["result"] == "PASS" for x in checks),
        "failed": sum(x["result"] == "FAIL" for x in checks)}
    output = ROOT / "data/seed/ddinter_spotcheck_report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Downloaded-source spot-check: {report['passed']}/{len(checks)} passed; live detail pages not checked.")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
