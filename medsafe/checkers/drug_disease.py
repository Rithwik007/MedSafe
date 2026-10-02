"""Exact-text matching for source-reviewed drug-disease rows."""
from __future__ import annotations

import csv
from pathlib import Path

from medsafe.core.normalizer import normalize_drug
from medsafe.explain.templates import (
    DISEASE_CHECKER_LIMITATION,
    DISEASE_NO_PATIENT_DATA,
    PHARMACIST_REVIEW_LINE,
    UNMATCHED_CONDITION,
)
from medsafe.models.domain import Evidence, Finding, FindingType, Prescription, Severity, UnresolvedItem

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "seed" / "drug_disease_rules.csv"


def _rows(path: Path = RULES_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [row for row in csv.DictReader(stream)
                if (row.get("reviewed_by") or "").strip()
                and (row.get("verified_on") or "").strip()
                and (row.get("source_url") or "").strip()]


def _text_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _ingredient_keys(value: str) -> set[str]:
    result = normalize_drug(value)
    if result.status != "matched" or not result.ingredients:
        return set()
    keys: set[str] = set()
    for ingredient in result.ingredients:
        normalized = normalize_drug(ingredient)
        if normalized.status == "matched" and normalized.ingredients:
            keys.update(item.casefold() for item in normalized.ingredients)
    return keys


def check_drug_disease(prescription: Prescription) -> tuple[list[Finding], list[UnresolvedItem]]:
    rules = _rows()
    conditions = prescription.patient.diagnoses
    orders = prescription.patient.current_meds + prescription.new_orders
    findings: list[Finding] = []
    unresolved: list[UnresolvedItem] = []
    rule_conditions = {_text_key(row.get("condition", "")) for row in rules
                       if _text_key(row.get("condition", ""))}

    for condition in conditions:
        condition_key = _text_key(condition)
        if not condition_key or condition_key not in rule_conditions:
            unresolved.append(UnresolvedItem(item=condition, reason=UNMATCHED_CONDITION))
            continue
        for row in rules:
            if condition_key != _text_key(row.get("condition", "")):
                continue
            rule_drug_keys = _ingredient_keys(row.get("drug", ""))
            matched_orders = [order.drug_name for order in orders
                              if rule_drug_keys & _ingredient_keys(order.drug_name)]
            if not matched_orders:
                continue
            category = row.get("label_category", "").strip()
            findings.append(Finding(
                type=FindingType.DRUG_DISEASE,
                severity=Severity.UNSPECIFIED,
                drugs_involved=list(dict.fromkeys(matched_orders)),
                reason=f"Label category: {category}. {row.get('reason', '').strip()}".strip(),
                recommendation=(row.get("recommendation", "").strip() + " " + PHARMACIST_REVIEW_LINE).strip(),
                rule_id=row["rule_id"].strip(),
                evidence=Evidence(
                    source_name=row.get("source_name", "").strip(),
                    source_url=row.get("source_url", "").strip() or None,
                    version_or_access_date=row.get("accessed_on", "").strip() or None,
                    review_status="Source text verified; not clinical review",
                    review_label="Source text verified; not clinical review",
                    rationale=row.get("source_section", "").strip() or None,
                ),
            ))
    return findings, unresolved


def drug_disease_checker_status(rule_count: int, has_patient_data: bool) -> tuple[str, str, int]:
    if rule_count == 0:
        return "NOT_RUN_NO_DATA", "No reviewed rows in drug_disease_rules.csv; checker not run.", 0
    reason = f"{rule_count} reviewed rows loaded. {DISEASE_CHECKER_LIMITATION}"
    if not has_patient_data:
        reason += " " + DISEASE_NO_PATIENT_DATA
    return "PARTIAL", reason, rule_count
