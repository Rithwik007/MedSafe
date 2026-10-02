"""Exact-ingredient matching for source-reviewed allergy rows."""
from __future__ import annotations

import csv
from pathlib import Path

from medsafe.core.normalizer import normalize_drug
from medsafe.explain.templates import (
    ALLERGY_CHECKER_LIMITATION,
    ALLERGY_NO_PATIENT_DATA,
    PHARMACIST_REVIEW_LINE,
    UNMATCHED_ALLERGEN,
)
from medsafe.models.domain import Evidence, Finding, FindingType, Prescription, Severity, UnresolvedItem

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "seed" / "allergy_rules.csv"


def _rows(path: Path = RULES_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [row for row in csv.DictReader(stream)
                if (row.get("reviewed_by") or "").strip()
                and (row.get("verified_on") or "").strip()
                and (row.get("source_url") or "").strip()]


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


def check_allergies(prescription: Prescription) -> tuple[list[Finding], list[UnresolvedItem]]:
    rules = _rows()
    allergies = prescription.patient.allergies
    orders = prescription.patient.current_meds + prescription.new_orders
    findings: list[Finding] = []
    unresolved: list[UnresolvedItem] = []
    rule_allergens: set[str] = set()
    for row in rules:
        rule_allergens.update(_ingredient_keys(row.get("allergen", "")))

    for allergy in allergies:
        allergy_keys = _ingredient_keys(allergy)
        if not allergy_keys or not (allergy_keys & rule_allergens):
            unresolved.append(UnresolvedItem(item=allergy, reason=UNMATCHED_ALLERGEN))
            continue
        for row in rules:
            allergen_keys = _ingredient_keys(row.get("allergen", ""))
            if not allergy_keys & allergen_keys:
                continue
            rule_drug_keys = _ingredient_keys(row.get("drug", ""))
            matched_orders = [order.drug_name for order in orders
                              if rule_drug_keys & _ingredient_keys(order.drug_name)]
            if not matched_orders:
                continue
            category = row.get("label_category", "").strip()
            findings.append(Finding(
                type=FindingType.ALLERGY,
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


def allergy_checker_status(rule_count: int, has_patient_data: bool) -> tuple[str, str, int]:
    if rule_count == 0:
        return "NOT_RUN_NO_DATA", "No reviewed rows in allergy_rules.csv; checker not run.", 0
    reason = f"{rule_count} reviewed rows loaded. {ALLERGY_CHECKER_LIMITATION}"
    if not has_patient_data:
        reason += " " + ALLERGY_NO_PATIENT_DATA
    return "PARTIAL", reason, rule_count
