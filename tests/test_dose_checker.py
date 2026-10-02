from __future__ import annotations

from fastapi.testclient import TestClient

import medsafe.checkers.dose as dose
import medsafe.checkers.engine as engine
from medsafe.api.app import app
from medsafe.checkers.dose import check_dose
from medsafe.checkers.stubs import CHECKER_COLUMNS
from medsafe.explain.templates import render_text
from medsafe.models.domain import MedOrder, Patient, Prescription
from medsafe.nlp.parser import parse_prescription


def _prescription(line: str, age: int | None = 35) -> Prescription:
    order = parse_prescription(line).orders[0]
    return Prescription(patient=Patient(age_years=age), new_orders=[order])


def _checker(prescription: Prescription):
    findings, unresolved, status, reason, count = check_dose(prescription)
    return findings, unresolved, status, reason, count


def test_over_daily_limit_emits_unspecified_finding_with_label_evidence():
    findings, unresolved, status, reason, count = _checker(
        _prescription("atorvastatin 40 mg 2 tabs TDS oral"))
    assert status == "PARTIAL" and count == 1
    assert "adult single-order checks only" in reason
    assert not unresolved
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity.value == "UNSPECIFIED"
    assert "240 mg per day" in finding.reason
    assert "label daily maximum 80 mg" in finding.reason
    assert "section 2.2 Recommended Dosage in Adult Patients" in finding.reason
    assert finding.evidence.source_url.startswith("https://dailymed.nlm.nih.gov/")
    assert "Pharmacist review required" in finding.recommendation


def test_at_limit_and_below_limit_emit_no_finding_or_reassurance():
    for line in ("atorvastatin 80 mg 1 tablet OD oral",
                 "atorvastatin 40 mg 1 tablet OD oral"):
        findings, unresolved, _status, _reason, _count = _checker(_prescription(line))
        assert findings == [] and unresolved == []
    report = engine.analyze(_prescription("atorvastatin 40 mg 1 tablet OD oral"))
    rendered = render_text(report).casefold()
    assert ("within" + " limit") not in rendered


def test_two_orders_are_checked_separately_not_summed():
    orders = [
        parse_prescription("atorvastatin 40 mg 1 tablet OD oral").orders[0],
        parse_prescription("atorvastatin 40 mg 1 tablet OD oral").orders[0],
    ]
    findings, unresolved, status, _reason, count = _checker(
        Prescription(patient=Patient(age_years=35), new_orders=orders))
    assert status == "PARTIAL" and count == 1
    assert findings == [] and unresolved == []


def test_age_missing_and_under_18_use_fixed_unresolved_wording():
    line = "atorvastatin 40 mg 1 tablet OD oral"
    _, missing, *_ = _checker(_prescription(line, age=None))
    _, underage, *_ = _checker(_prescription(line, age=17))
    assert [item.reason for item in missing] == ["dose not checked: patient age not provided"]
    assert [item.reason for item in underage] == ["dose not checked: row covers adults only"]


def test_low_medium_confidence_and_missing_quantity_abstain():
    line = "atorvastatin 40 mg 2 tablets TDS oral"
    parsed = parse_prescription(line).orders[0]
    assert parsed.parse_confidence == "MEDIUM"
    _, unresolved, *_ = _checker(_prescription(line))
    assert unresolved[0].reason == "dose not checked: parse confidence is not HIGH"

    low_confidence = parsed.model_copy(update={"parse_confidence": "LOW"})
    _, unresolved, *_ = _checker(Prescription(patient=Patient(age_years=35),
                                                new_orders=[low_confidence]))
    assert unresolved[0].reason == "dose not checked: parse confidence is not HIGH"

    high_no_quantity = parsed.model_copy(update={"parse_confidence": "HIGH",
                                                  "units_per_intake": None})
    _, unresolved, *_ = _checker(Prescription(patient=Patient(age_years=35),
                                                new_orders=[high_no_quantity]))
    assert unresolved[0].reason == "dose not checked: quantity per intake is unknown"


def test_unit_frequency_prn_one_time_and_route_mismatch_abstain():
    cases = [
        ("atorvastatin 40 mcg 1 tablet OD oral", "dose not checked: order unit does not match the label row"),
        ("atorvastatin 80 mg 1 tablet SOS oral", "dose not checked: as-needed order has no fixed daily frequency"),
        ("atorvastatin 80 mg 1 tablet STAT oral", "dose not checked: one-time order is not a daily schedule"),
    ]
    for line, expected in cases:
        _, unresolved, *_ = _checker(_prescription(line))
        assert unresolved and unresolved[0].reason == expected

    route_mismatch = parse_prescription("atorvastatin 40 mg 1 tablet OD oral").orders[0].model_copy(
        update={"route": "iv"})
    _, unresolved, *_ = _checker(Prescription(patient=Patient(age_years=35),
                                                new_orders=[route_mismatch]))
    assert unresolved[0].reason == "dose not checked: route does not match the label row"

    unknown = parse_prescription("atorvastatin 40 mg 1 tablet oral").orders[0].model_copy(
        update={"parse_confidence": "HIGH", "frequency_code": None, "frequency_per_day": None})
    _, unresolved, *_ = _checker(Prescription(patient=Patient(age_years=35), new_orders=[unknown]))
    assert unresolved[0].reason == "dose not checked: frequency is unknown"


def test_empty_reviewed_data_reports_not_run_no_data(tmp_path, monkeypatch):
    empty = tmp_path / "dose_limits.csv"
    empty.write_text(",".join(CHECKER_COLUMNS["dose_limits.csv"]) + "\n", encoding="utf-8")
    monkeypatch.setattr(dose, "RULES_PATH", empty)
    findings, unresolved, status, reason, count = dose.check_dose(_prescription(
        "atorvastatin 40 mg 1 tablet OD oral"))
    assert findings == [] and unresolved == []
    assert status == "NOT_RUN_NO_DATA" and count == 0
    assert "checker not run" in reason


def test_other_checker_and_ml_outputs_do_not_depend_on_dose(monkeypatch):
    prescription = _prescription("atorvastatin 40 mg 2 tabs TDS oral")
    with_dose = engine.analyze(prescription)
    real_checker = engine.check_dose
    monkeypatch.setattr(engine, "check_dose", lambda _p: (
        [], [], "NOT_RUN_NO_DATA", "No reviewed rows in dose_limits.csv; checker not run.", 0))
    without_dose = engine.analyze(prescription)
    monkeypatch.setattr(engine, "check_dose", real_checker)
    projection = lambda report: {
        "findings": [item.model_dump(mode="json") for item in report.findings
                     if item.type.value != "DOSE"],
        "ml_status": report.ml_status.model_dump(mode="json") if report.ml_status else None,
        "checker_status": [item.model_dump(mode="json") for item in report.checker_status
                           if item.checker != "DOSE"],
    }
    assert projection(with_dose) == projection(without_dose)


def test_api_surfaces_dose_finding_and_missing_age_unresolved():
    with TestClient(app) as client:
        response = client.post("/analyze-text?use_llm=false", json={
            "patient": {"age_years": 35},
            "prescription_text": "atorvastatin 40 mg 2 tabs TDS oral",
        })
        missing_age = client.post("/analyze-text?use_llm=false", json={
            "patient": {},
            "prescription_text": "atorvastatin 40 mg 1 tablet OD oral",
        })
    assert response.status_code == 200
    report = response.json()
    assert any(item["type"] == "DOSE" for item in report["findings"])
    assert next(row for row in report["checker_status"] if row["checker"] == "DOSE")["status"] == "PARTIAL"
    assert missing_age.status_code == 200
    assert any(item["reason"] == "dose not checked: patient age not provided"
               for item in missing_age.json()["unresolved_items"])
