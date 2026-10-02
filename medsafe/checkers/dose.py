"""Single-order dose comparison using only reviewed local label rows."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from medsafe.core.normalizer import normalize_drug
from medsafe.explain.templates import (
    DOSE_CHECKER_LIMITATION,
    DOSE_REVIEW_LINE,
    DOSE_SINGLE_ORDER_TRIGGER,
    DOSE_SOURCE_WHY,
    DOSE_UNRESOLVED,
    dose_exceeded_text,
)
from medsafe.models.domain import Evidence, Finding, FindingType, Prescription, Severity, UnresolvedItem

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "seed" / "dose_limits.csv"


def _rows(path: Path | None = None) -> list[dict[str, str]]:
    path = path or RULES_PATH
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [row for row in csv.DictReader(stream)
                if (row.get("reviewed_by") or "").strip()
                and (row.get("verified_on") or "").strip()
                and (row.get("source_url") or "").strip()]


def _same_ingredient(left: str, right: str) -> bool:
    left_result, right_result = normalize_drug(left), normalize_drug(right)
    return (left_result.status == "matched" and right_result.status == "matched"
            and len(left_result.ingredients) == len(right_result.ingredients) == 1
            and left_result.ingredients[0].casefold() == right_result.ingredients[0].casefold())


def _decimal(value: str | float | int) -> Decimal:
    return Decimal(str(value))


def _number(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _unresolved(order_name: str, reason_code: str) -> UnresolvedItem:
    return UnresolvedItem(item=order_name, reason=DOSE_UNRESOLVED[reason_code])


def check_dose(prescription: Prescription
               ) -> tuple[list[Finding], list[UnresolvedItem], str, str, int]:
    rows = _rows()
    if not rows:
        return [], [], "NOT_RUN_NO_DATA", "No reviewed rows in dose_limits.csv; checker not run.", 0

    findings: list[Finding] = []
    unresolved: list[UnresolvedItem] = []
    for order in prescription.new_orders:
        row = next((candidate for candidate in rows
                    if _same_ingredient(order.drug_name, candidate.get("drug", ""))), None)
        if row is None:
            continue

        population = (row.get("population") or "").casefold()
        if "adult" in population:
            age = prescription.patient.age_years
            if age is None:
                unresolved.append(_unresolved(order.drug_name, "PATIENT_AGE_MISSING"))
                continue
            if age < 18:
                unresolved.append(_unresolved(order.drug_name, "ADULTS_ONLY"))
                continue

        if order.parse_confidence != "HIGH":
            unresolved.append(_unresolved(order.drug_name, "PARSE_CONFIDENCE"))
            continue
        if order.units_per_intake is None:
            unresolved.append(_unresolved(order.drug_name, "QUANTITY_UNKNOWN"))
            continue
        unit = (row.get("dose_unit") or "").strip()
        if order.dose_unit != unit:
            unresolved.append(_unresolved(order.drug_name, "UNIT_MISMATCH"))
            continue
        if order.as_needed:
            unresolved.append(_unresolved(order.drug_name, "AS_NEEDED"))
            continue
        if order.one_time:
            unresolved.append(_unresolved(order.drug_name, "ONE_TIME"))
            continue
        if order.frequency_code is None or order.frequency_per_day is None:
            unresolved.append(_unresolved(order.drug_name, "FREQUENCY_UNKNOWN"))
            continue
        if (not order.route or order.route_is_assumed
                or order.route.casefold() != (row.get("route") or "").strip().casefold()):
            unresolved.append(_unresolved(order.drug_name, "ROUTE_MISMATCH"))
            continue
        if order.dose_value is None:
            unresolved.append(_unresolved(order.drug_name, "QUANTITY_UNKNOWN"))
            continue

        try:
            per_intake = _decimal(order.dose_value) * _decimal(order.units_per_intake)
            daily_total = per_intake * _decimal(order.frequency_per_day)
            max_single = _decimal(row["max_single_dose"])
            max_daily = _decimal(row["max_daily_dose"])
        except (InvalidOperation, KeyError, ValueError):
            unresolved.append(_unresolved(order.drug_name, "QUANTITY_UNKNOWN"))
            continue
        if per_intake <= max_single and daily_total <= max_daily:
            continue

        source_section = (row.get("source_section") or "").strip()
        message = dose_exceeded_text(row["rule_id"], source_section, _number(daily_total),
            _number(max_daily), _number(per_intake), _number(max_single), unit)
        findings.append(Finding(
            type=FindingType.DOSE,
            severity=Severity.UNSPECIFIED,
            drugs_involved=[order.drug_name],
            reason=message,
            recommendation=DOSE_REVIEW_LINE,
            rule_id=row["rule_id"].strip(),
            evidence=Evidence(
                source_name=(row.get("source_name") or "").strip(),
                source_url=(row.get("source_url") or "").strip() or None,
                version_or_access_date=(row.get("accessed_on") or "").strip() or None,
                review_status="Source text verified; not clinical review",
                review_label="Source text verified; not clinical review",
                rationale=source_section or None,
            ),
        ))

    limitation = DOSE_CHECKER_LIMITATION
    status_reason = f"{len(rows)} reviewed dose row(s) loaded. {limitation}"
    return findings, unresolved, "PARTIAL", status_reason, len(rows)
