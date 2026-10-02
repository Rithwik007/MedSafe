"""Import whitelisted DDInter pair/severity rows; never synthesize missing clinical text."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PAGE = "https://ddinter.scbdd.com/download/"
SOURCE_TERMS = "https://ddinter.scbdd.com/terms/"
SEVERITY_MAP = {"contraindicated": "CONTRAINDICATED", "major": "MAJOR", "moderate": "MODERATE", "minor": "MINOR", "unknown": "UNSPECIFIED"}
SEVERITY_RANK = {"CONTRAINDICATED": 5, "MAJOR": 4, "MODERATE": 3, "UNSPECIFIED": 2, "MINOR": 1}
OUTPUT_FIELDS = [
    "rule_id", "type", "drugs", "severity", "reason", "mechanism", "recommendation",
    "source_name", "source_url", "version_or_access_date", "review_status", "reviewed_by",
    "verified_on", "trigger", "license",
]


def read_whitelist(path: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        name = line.strip().lstrip("\ufeff")
        if name and not name.startswith("#"):
            names[name.casefold()] = name
    return names


def import_ddinter(raw_dir: Path, whitelist_path: Path, output_path: Path) -> dict[str, object]:
    whitelist = read_whitelist(whitelist_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: dict[tuple[str, str], dict[str, str]] = {}
    counts: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    source_levels: Counter[str] = Counter()
    conflicts: list[dict[str, str]] = []
    per_drug: Counter[str] = Counter()
    source_rows = 0
    whitelist_pair_rows = 0
    imported: list[dict[str, str]] = []
    files = sorted(raw_dir.glob("ddinter_downloads_code_*.csv"))
    if not files:
        raise FileNotFoundError(f"No DDInter CSV files found in {raw_dir}")

    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"DDInterID_A", "Drug_A", "DDInterID_B", "Drug_B", "Level"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError(f"Unexpected DDInter columns in {path.name}: {reader.fieldnames}")
            for row in reader:
                source_rows += 1
                name_a = (row.get("Drug_A") or "").strip()
                name_b = (row.get("Drug_B") or "").strip()
                if not name_a or not name_b:
                    counts["missing_drug_name"] += 1
                    continue
                if name_a.casefold() not in whitelist or name_b.casefold() not in whitelist:
                    continue
                whitelist_pair_rows += 1
                source_level = (row.get("Level") or "").strip()
                source_levels[source_level or "<blank>"] += 1
                severity = SEVERITY_MAP.get(source_level.casefold())
                if severity is None:
                    unmapped[source_level or "<blank>"] += 1
                    continue
                pair = tuple(sorted((name_a.casefold(), name_b.casefold())))
                if pair in seen:
                    counts["duplicate_pair"] += 1
                    existing = seen[pair]
                    if existing["severity"] != severity:
                        counts["severity_conflict_pair_rows"] += 1
                        counts[f"severity_conflict:{existing['severity']}:{severity}"] += 1
                        kept_severity = max((existing["severity"], severity), key=SEVERITY_RANK.get)
                        conflicts.append({"drug_a": existing["drugs"].split("|")[0],
                            "drug_b": existing["drugs"].split("|")[1],
                            "first_severity": existing["severity"], "duplicate_severity": severity,
                            "kept_severity": kept_severity})
                        if SEVERITY_RANK[severity] > SEVERITY_RANK[existing["severity"]]:
                            existing["severity"] = severity
                            existing["reason"] = f"DDInter lists this pair at risk level {source_level}."
                    continue
                ddinter_id = "-".join(sorted((row["DDInterID_A"].strip(), row["DDInterID_B"].strip())))
                # Current downloadable CSV has no mechanism/management columns.
                mechanism = row.get("Mechanism") or row.get("mechanism") or ""
                recommendation = row.get("Management") or row.get("Recommendation") or ""
                rule = {
                    "rule_id": f"DDINTER-{ddinter_id}",
                    "type": "DDI",
                    "drugs": "|".join((name_a, name_b)),
                    "severity": severity,
                    "reason": f"DDInter lists this pair at risk level {source_level}.",
                    "mechanism": mechanism.strip(),
                    "recommendation": recommendation.strip(),
                    "source_name": "DDInter downloadable interaction dataset",
                    "source_url": SOURCE_PAGE,
                    "version_or_access_date": "Downloaded 2026-09-30",
                    "review_status": "dataset_imported_not_independently_clinically_reviewed",
                    "reviewed_by": "",
                    "verified_on": "",
                    "trigger": "",
                    "license": "CC BY-NC-SA 4.0; noncommercial use only",
                }
                seen[pair] = rule
                imported.append(rule)
                counts[severity] += 1
                per_drug[name_a.casefold()] += 1
                per_drug[name_b.casefold()] += 1
    imported.sort(key=lambda x: x["rule_id"])
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(imported)
    zero_rule_drugs = sorted(name for key, name in whitelist.items() if per_drug[key] == 0)
    report = {
        "source": "DDInter downloadable interaction CSV",
        "source_url": SOURCE_PAGE,
        "terms_url": SOURCE_TERMS,
        "license": "CC BY-NC-SA 4.0; noncommercial use only",
        "downloaded_on": "2026-09-30",
        "files": len(files),
        "source_rows": source_rows,
        "whitelist_drugs": len(whitelist),
        "whitelist_pair_rows": whitelist_pair_rows,
        "imported_unique_rules": len(imported),
        "mapped_severity_counts": {k: counts[k] for k in ("CONTRAINDICATED", "MAJOR", "MODERATE", "UNSPECIFIED", "MINOR") if counts[k]},
        "unmapped_severity_rows_skipped": sum(unmapped.values()),
        "unmapped_severity_labels": dict(unmapped),
        "source_severity_label_counts": dict(source_levels),
        "duplicate_pair_rows_skipped": counts["duplicate_pair"],
        "duplicate_severity_conflicts": conflicts,
        "missing_drug_name_rows_skipped": counts["missing_drug_name"],
        "zero_rule_whitelist_drugs": zero_rule_drugs,
        "rules_per_drug": {whitelist[key]: per_drug[key] for key in sorted(whitelist)},
        "output": str(output_path),
        "clinical_review_status": "dataset imported; not independently clinically reviewed",
    }
    report_path = output_path.with_name("ddinter_import_report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = ["# DDInter import audit", "", f"- Whitelist pair rows: {whitelist_pair_rows}",
                f"- Unique imported rules: {len(imported)}", "- Source severity labels (raw whitelist rows):"]
    markdown += [f"  - `{label}`: {count}" for label, count in sorted(source_levels.items())]
    markdown += ["- Unmapped source severity labels skipped:"]
    markdown += [f"  - `{label}`: {count}" for label, count in sorted(unmapped.items())] or ["  - None"]
    markdown += ["- Imported severity counts:"]
    markdown += [f"  - `{severity}`: {counts[severity]}" for severity in ("CONTRAINDICATED", "MAJOR", "MODERATE", "UNSPECIFIED", "MINOR")]
    markdown += [f"- Duplicate pair rows: {counts['duplicate_pair']}",
                 f"- Duplicate severity conflict rows: {counts['severity_conflict_pair_rows']}",
                 f"- Missing drug-name rows skipped: {counts['missing_drug_name']}",
                 f"- Zero-rule whitelist drugs: {', '.join(zero_rule_drugs) or 'None'}", ""]
    if conflicts:
        markdown[-1:-1] = ["- Severity conflicts:"] + [f"  - {c['drug_a']} + {c['drug_b']}: {c['first_severity']} vs {c['duplicate_severity']}; kept {c['kept_severity']}" for c in conflicts]
    markdown_path = (ROOT / "reports/ddinter_import.md" if output_path.parent.resolve() == (ROOT / "data/seed").resolve()
                     else output_path.parent / "ddinter_import.md")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")
    return {**report, "imported": len(imported), "counts": dict(counts),
            "unmapped_levels": dict(unmapped), "report": str(report_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/ddinter")
    parser.add_argument("--whitelist", type=Path, default=ROOT / "data/seed/drug_whitelist.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/seed/rules.csv")
    args = parser.parse_args()
    result = import_ddinter(args.raw_dir, args.whitelist, args.output)
    print(f"Read {result['files']} files; imported {result['imported']} pair rules from {result['whitelist_drugs']} whitelist drugs.")
    print(f"Mapped unique severity counts: {result['mapped_severity_counts']}")
    print(f"Raw source label counts: {result['source_severity_label_counts']}")
    print(f"Unmapped severity labels (skipped): {result['unmapped_levels']}")
    print(f"Audit report: {result['report']}")
    print(f"Output: {result['output']}")


if __name__ == "__main__":
    main()
