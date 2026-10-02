from medsafe.core.report import SafetyReport
from medsafe.explain.templates import explain_finding, render_text
from medsafe.models.domain import Evidence, Finding, FindingType, Severity


def _finding(**overrides):
    values = dict(type=FindingType.DDI, severity=Severity.MAJOR,
        drugs_involved=["Warfarin", "Ibuprofen"], reason="DDInter lists this pair at Major severity.",
        mechanism="", recommendation="", rule_id="R1",
        evidence=Evidence(source_name="DDInter", source_url="https://example.test/download",
            review_status="imported", ddinter_ids=["DDInter1", "DDInter2"]))
    values.update(overrides)
    return Finding(**values)


def test_blank_mechanism_uses_exact_source_dataset_fallback():
    assert explain_finding(_finding()).why == "Mechanism not provided by the source dataset."


def test_reviewed_fixture_mechanism_is_shown_verbatim():
    finding = _finding(mechanism="TEST MECHANISM TEXT",
        evidence=Evidence(source_name="Fixture", review_status="reviewed", review_label="Reviewed"))
    assert explain_finding(finding).why == "TEST MECHANISM TEXT"


def test_unreviewed_ddi_uses_exact_recommendation_fallback():
    assert explain_finding(_finding()).recommendation == (
        "No management guidance in the source dataset. Ask a pharmacist or check an authoritative label.")


def test_unspecified_adds_source_severity_note():
    finding = _finding(severity=Severity.UNSPECIFIED)
    assert explain_finding(finding).recommendation.endswith("Severity was not classified by the source.")


def test_duplicate_headline_uses_short_duplicate_form():
    finding = _finding(type=FindingType.DUPLICATE)
    assert explain_finding(finding).headline == "MAJOR: Duplicate Warfarin + Ibuprofen"


def test_risk_is_one_sentence_and_trigger_holds_details():
    result = explain_finding(_finding(drugs_involved=["Brand A", "Brand B"],
        reason=("DDInter lists this pair at risk level Major. "
        "Ingredient pair: warfarin + ibuprofen. Orders involved: Brand A, Brand B.")))
    assert result.risk == "DDInter lists this pair at Major severity."
    assert result.risk != result.trigger
    assert "Orders involved" not in result.risk
    assert result.trigger == "Ingredients: warfarin + ibuprofen. Orders: Brand A, Brand B."


def test_duplicate_why_is_not_applicable():
    finding = _finding(type=FindingType.DUPLICATE)
    assert explain_finding(finding).why == "Not applicable to duplicate-therapy findings."


def test_demo_snapshot_combiflam_dolo_warfarin():
    from pathlib import Path
    from medsafe.checkers.engine import MlPredictor, analyze
    from medsafe.kb.rules import RULES
    from medsafe.models.domain import MedOrder, Patient, Prescription

    from datetime import datetime, timezone
    fixed_time = datetime(2026, 9, 30, tzinfo=timezone.utc)
    names = frozenset(name.casefold() for rule in RULES
        if rule.kind.value == "DDI" and rule.severity.value == "UNSPECIFIED"
        for name in rule.drugs)
    predictor = MlPredictor(lambda _left, _right: ("Minor", 0.96), names,
        model_version="fake-snapshot-model", tau=0.70,
        model_fingerprint="fake-snapshot-fingerprint", reason="Fake predictor for snapshot.")
    report = analyze(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Combiflam")]),
        new_orders=[MedOrder(drug_name="Dolo 650"), MedOrder(drug_name="Warfarin")]),
        clock=lambda: fixed_time, ml_predictor=predictor)
    text = render_text(report)
    snapshot = Path(__file__).parent / "snapshots" / "combiflam_dolo_warfarin.txt"
    assert text + "\n" == snapshot.read_text(encoding="utf-8")
    assert "Checkers: 1 RAN, 4 PARTIAL, 0 NOT_RUN_NO_DATA." in text
    assert "Combiflam, Warfarin" in text and "Dolo 650" in text
    assert "paracetamol" in text
    assert "Acetaminophen" not in text
    assert "project design choice, not a clinical rule" not in text
    assert "ALLERGY: PARTIAL" in text
    assert "DRUG_DISEASE: PARTIAL" in text
    assert "DOSE: PARTIAL" in text
    assert "Not applicable to duplicate-therapy findings." in text
    assert "Ingredients: warfarin + ibuprofen. Orders: Combiflam, Warfarin." in text
    assert "Shared ingredient: paracetamol. Orders: Combiflam, Dolo 650." in text
    assert text.count("Risk:") == text.count("Trigger:")
