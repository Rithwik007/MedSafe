import csv
import json
from pathlib import Path

from medsafe.checkers import engine
from medsafe.core.report import SafetyReport
from medsafe.explain.templates import render_text
from medsafe.models.domain import FindingType, MedOrder, Patient, Prescription, Severity

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"


def _read_rows(name):
    with (SEED / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _finding(report, kind):
    return next(item for item in report.findings if item.type == kind)


def test_allergy_direct_match_uses_promoted_row_text_and_unknown_severity():
    row = _read_rows("allergy_rules.csv")[0]
    report = engine.analyze(Prescription(patient=Patient(allergies=[row["allergen"]]),
        new_orders=[MedOrder(drug_name=row["drug"])]))
    finding = _finding(report, FindingType.ALLERGY)
    assert finding.rule_id == row["rule_id"]
    assert finding.severity == Severity.UNSPECIFIED
    assert row["reason"] in finding.reason
    assert f"Label category: {row['label_category']}" in finding.reason
    assert row["recommendation"] in finding.recommendation
    assert "Ask a pharmacist" in finding.recommendation
    assert finding.evidence.review_label == "Source text verified; not clinical review"


def test_drug_disease_exact_match_uses_promoted_row_text():
    row = _read_rows("drug_disease_rules.csv")[0]
    report = engine.analyze(Prescription(patient=Patient(diagnoses=[row["condition"]]),
        new_orders=[MedOrder(drug_name=row["drug"])]))
    finding = _finding(report, FindingType.DRUG_DISEASE)
    assert finding.rule_id == row["rule_id"]
    assert finding.severity == Severity.UNSPECIFIED
    assert row["reason"] in finding.reason
    assert f"Label category: {row['label_category']}" in finding.reason
    assert row["recommendation"] in finding.recommendation
    assert "Ask a pharmacist" in finding.recommendation


def test_nonmatching_allergen_and_condition_are_unresolved_not_findings():
    report = engine.analyze(Prescription(patient=Patient(
        allergies=["unlisted allergen"], diagnoses=["myasthenia gravis, unspecified"]),
        new_orders=[MedOrder(drug_name="Amoxicillin"), MedOrder(drug_name="Ciprofloxacin")]))
    assert not any(item.type in {FindingType.ALLERGY, FindingType.DRUG_DISEASE}
                   for item in report.findings)
    unresolved = {item.item: item.reason for item in report.unresolved_items}
    assert "unlisted allergen" in unresolved
    assert "myasthenia gravis, unspecified" in unresolved
    assert "does not establish absence of a concern" in unresolved["unlisted allergen"]
    assert "does not establish absence of a concern" in unresolved["myasthenia gravis, unspecified"]


def test_missing_patient_inputs_are_explicit_in_partial_status():
    report = engine.analyze(Prescription(patient=Patient(), new_orders=[MedOrder(drug_name="Warfarin")]))
    status = {item.checker: item for item in report.checker_status}
    assert status["ALLERGY"].status == "PARTIAL"
    assert "No patient allergy data supplied" in status["ALLERGY"].reason
    assert status["DRUG_DISEASE"].status == "PARTIAL"
    assert "No patient condition data supplied" in status["DRUG_DISEASE"].reason
    assert status["DOSE"].status == "PARTIAL"
    assert status["DOSE"].rules_loaded == 1
    assert "adult single-order checks only" in status["DOSE"].reason


def test_clinical_checkers_do_not_change_ddi_or_ml_payload(monkeypatch):
    from medsafe.checkers.engine import MlPredictor
    from medsafe.kb.rules import RULES

    names = frozenset(name.casefold() for rule in RULES
        if rule.kind.value == "DDI" and rule.severity.value == "UNSPECIFIED"
        for name in rule.drugs)
    predictor = MlPredictor(lambda _left, _right: ("Minor", 0.96), names,
        model_version="test", tau=0.70, model_fingerprint="test-sha",
        reason="Test predictor.")
    prescription = Prescription(patient=Patient(allergies=["amoxicillin"],
        diagnoses=["myasthenia gravis"]), new_orders=[
            MedOrder(drug_name="Combiflam"), MedOrder(drug_name="Warfarin"),
            MedOrder(drug_name="Amoxicillin"), MedOrder(drug_name="Ciprofloxacin")])
    on_report = engine.analyze(prescription, ml_predictor=predictor)
    on_ddi = json.dumps([item.model_dump(mode="json") for item in on_report.findings
                         if item.type == FindingType.DDI], sort_keys=True, separators=(",", ":")).encode()
    on_ml = on_report.ml_status.model_dump_json().encode()
    monkeypatch.setattr(engine, "check_allergies", lambda _: ([], []))
    monkeypatch.setattr(engine, "check_drug_disease", lambda _: ([], []))
    off_report = engine.analyze(prescription, ml_predictor=predictor)
    off_ddi = json.dumps([item.model_dump(mode="json") for item in off_report.findings
                          if item.type == FindingType.DDI], sort_keys=True, separators=(",", ":")).encode()
    off_ml = off_report.ml_status.model_dump_json().encode()
    assert on_ddi == off_ddi
    assert on_ml == off_ml


def test_python_files_do_not_contain_clinical_row_reason_or_recommendation():
    rows = _read_rows("allergy_rules.csv") + _read_rows("drug_disease_rules.csv")
    ignored = {".pytest_cache", "__pycache__", ".venv", "node_modules"}
    python_text = "\\n".join(path.read_text(encoding="utf-8")
        for path in ROOT.rglob("*.py")
        if not any(part in ignored for part in path.relative_to(ROOT).parts))
    for row in rows:
        assert row["reason"] not in python_text
        assert row["recommendation"] not in python_text


def test_rendered_checker_output_has_no_rule_7_banned_phrases():
    report = engine.analyze(Prescription(patient=Patient(allergies=["amoxicillin"],
        diagnoses=["myasthenia gravis"]), new_orders=[
            MedOrder(drug_name="Amoxicillin"), MedOrder(drug_name="Ciprofloxacin")]))
    text = render_text(report).casefold()
    assert all(phrase not in text for phrase in ("safe to use", "no risk", "approved"))
