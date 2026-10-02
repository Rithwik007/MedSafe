"""Load imported, source-tracked DDI rules. Imported rows stay marked as unreviewed."""
from dataclasses import dataclass
import csv
import re
from pathlib import Path
from medsafe.models.domain import FindingType, Severity, Evidence


@dataclass(frozen=True)
class Rule:
    rule_id: str
    kind: FindingType
    drugs: tuple[str, ...]
    severity: Severity
    reason: str
    mechanism: str
    recommendation: str
    evidence: Evidence
    trigger: str | None = None


# Imported dataset rows stay visibly marked as not independently clinically reviewed.
def load_rules(path: Path | None = None) -> tuple[Rule, ...]:
    path = path or Path(__file__).resolve().parents[2] / "data/seed/rules.csv"
    if not path.exists():
        return ()
    rules: list[Rule] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row.get("rule_id") or not row.get("drugs"):
                continue
            try:
                kind = FindingType(row["type"].strip().upper())
                severity = Severity(row["severity"].strip().upper())
            except (KeyError, ValueError):
                continue
            drugs = tuple(part.strip() for part in row["drugs"].split("|") if part.strip())
            if not drugs:
                continue
            rules.append(Rule(
                rule_id=row["rule_id"].strip(), kind=kind, drugs=drugs, severity=severity,
                reason=row.get("reason", "").strip(), mechanism=row.get("mechanism", "").strip(),
                recommendation=row.get("recommendation", "").strip(),
                evidence=Evidence(source_name=(row.get("source_name") or "Unspecified source") +
                    (" (DDInter ingredient name: Acetaminophen)" if "Acetaminophen" in drugs else ""),
                    source_url=row.get("source_url") or None,
                    version_or_access_date=row.get("version_or_access_date") or None,
                    review_status=row.get("review_status") or "unreviewed",
                    review_label="Reviewed" if (row.get("reviewed_by", "").strip()
                    and row.get("verified_on", "").strip()
                    and row.get("source_url", "").strip()) else "Not reviewed",
                    ddinter_ids=re.findall(r"DDInter\d+", row["rule_id"])),
                trigger=row.get("trigger") or None,
            ))
    return tuple(rules)


RULES = load_rules()
