from medsafe.api.app import app
from fastapi.testclient import TestClient
from medsafe.checkers.engine import analyze
from medsafe.core.report import SafetyReport
from medsafe.models.domain import Evidence, Finding, FindingType, MedOrder, Patient, Prescription, Severity

client = TestClient(app)


def _finding(kind, severity, rule_id="fixture", pair=("Metformin", "Warfarin")):
    return Finding(type=kind, severity=severity, drugs_involved=list(pair),
        reason="Fixture reason.", recommendation="Fixture recommendation.", rule_id=rule_id,
        evidence=Evidence(source_name="Fixture", review_status="fixture"))


def test_checker_status_has_clinical_checkers_partial_and_dose_partial():
    report = analyze(Prescription(patient=Patient(), new_orders=[MedOrder(drug_name="Warfarin")]))
    active = [item for item in report.checker_status if item.status in {"RAN", "PARTIAL"}]
    no_data = [item for item in report.checker_status if item.status == "NOT_RUN_NO_DATA"]
    assert len(active) == 5
    assert no_data == []
    clinical = {item.checker: item for item in active if item.checker in {"ALLERGY", "DRUG_DISEASE"}}
    assert all(item.status == "PARTIAL" and item.rules_loaded == 5 for item in clinical.values())
    assert all("handful" in item.reason for item in clinical.values())
    assert next(item for item in active if item.checker == "DOSE").rules_loaded == 1


def test_overall_statement_has_required_caution_and_no_banned_phrases():
    report = analyze(Prescription(patient=Patient(), new_orders=[MedOrder(drug_name="Warfarin")]))
    text = report.overall_statement.casefold()
    assert "checkers: 1 ran, 4 partial, 0 not_run_no_data" in text
    assert "does not mean" in text
    assert all(banned not in text for banned in ("safe to use", "no risk", "approved"))


def test_empty_prescription_returns_report_and_disclaimer():
    report = analyze(Prescription(patient=Patient(), new_orders=[]))
    assert isinstance(report, SafetyReport)
    assert report.findings == []
    assert "qualified clinician" in report.disclaimer
    assert "does not mean" in report.overall_statement


def test_unresolved_and_suggested_names_never_become_findings():
    report = analyze(Prescription(patient=Patient(), new_orders=[
        MedOrder(drug_name="mystery pill"), MedOrder(drug_name="Warfrin")]))
    assert any(item.item == "mystery pill" for item in report.unresolved_items)
    assert not any(item.item == "knowledge base" for item in report.unresolved_items)
    assert [item.item for item in report.suggested_matches] == ["Warfrin"]
    assert all("mystery pill" not in finding.drugs_involved and "Warfrin" not in finding.drugs_involved
               for finding in report.findings)


def test_finding_defaults_serialize_and_api_includes_additive_fields():
    finding = _finding(FindingType.DDI, Severity.MAJOR)
    data = finding.model_dump()
    assert data["explanation"] is None
    assert data["evidence"]["rationale"] is None
    assert data["evidence"]["ddinter_ids"] == []
    response = client.post("/analyze", json={"patient": {"current_meds": [{"drug_name": "Warfarin"}]},
        "new_orders": [{"drug_name": "Ibuprofen"}]})
    assert response.status_code == 200
    warning = response.json()["findings"][0]
    assert "explanation" in warning
    assert "rationale" in warning["evidence"]
    assert "ddinter_ids" in warning["evidence"]


def test_report_has_deterministic_findings_for_same_input():
    prescription = Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Warfarin")]),
        new_orders=[MedOrder(drug_name="Ibuprofen")])
    first, second = analyze(prescription), analyze(prescription)
    assert [item.model_dump() for item in first.findings] == [item.model_dump() for item in second.findings]
    assert first.checker_status == second.checker_status
    assert first.kb_fingerprint == second.kb_fingerprint


def test_analyze_uses_injected_utc_clock():
    from datetime import datetime, timezone
    fixed = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    report = analyze(Prescription(patient=Patient(), new_orders=[]), clock=lambda: fixed)
    assert report.generated_at == "2025-02-03T04:05:00+00:00"


def test_finding_sort_orders_severity_then_type_then_rule(monkeypatch):
    import medsafe.checkers.engine as engine
    items = [_finding(FindingType.DUPLICATE, Severity.MODERATE, "z"),
             _finding(FindingType.DDI, Severity.MODERATE, "b"),
             _finding(FindingType.DDI, Severity.MAJOR, "c"),
             _finding(FindingType.DDI, Severity.MODERATE, "a")]
    monkeypatch.setattr(engine, "check_duplicates", lambda _: SafetyReport(findings=[items[0]]))
    monkeypatch.setattr(engine, "check_ddi", lambda _: items[1:])
    report = engine.analyze(Prescription(patient=Patient(), new_orders=[MedOrder(drug_name="Warfarin")]))
    assert [item.rule_id for item in report.findings] == ["c", "a", "b", "z"]


def test_cross_checker_duplicate_rule_and_pair_collapses(monkeypatch):
    import medsafe.checkers.engine as engine
    ddi = _finding(FindingType.DDI, Severity.MAJOR, "same-rule")
    duplicate = _finding(FindingType.DUPLICATE, Severity.MODERATE, "same-rule")
    monkeypatch.setattr(engine, "check_duplicates", lambda _: SafetyReport(findings=[duplicate]))
    monkeypatch.setattr(engine, "check_ddi", lambda _: [ddi])
    report = engine.analyze(Prescription(patient=Patient(), new_orders=[MedOrder(drug_name="Warfarin")]))
    assert len([item for item in report.findings if item.rule_id == "same-rule"]) == 1


def test_fingerprint_changes_when_seed_csv_row_changes(tmp_path, monkeypatch):
    import medsafe.checkers.engine as engine
    seed = tmp_path / "data" / "seed"
    seed.mkdir(parents=True)
    source = seed / "fixture.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    before = engine.kb_fingerprint()
    source.write_text("a\n2\n", encoding="utf-8")
    assert engine.kb_fingerprint() != before


def test_fingerprint_changes_when_severity_policy_changes(tmp_path, monkeypatch):
    from medsafe.checkers import engine

    seed = tmp_path / "data" / "seed"
    seed.mkdir(parents=True)
    (seed / "severity_policy.csv").write_text("label_category,severity\nWARNING,MAJOR\n")
    (seed / "conditions.csv").write_text("condition_id,display_name,synonym\n")
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    before = engine.kb_fingerprint()
    (seed / "severity_policy.csv").write_text("label_category,severity\nWARNING,MODERATE\n")
    assert engine.kb_fingerprint() != before
