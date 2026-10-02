from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

from medsafe.checkers import engine
from medsafe.core.report import SafetyReport
from medsafe.explain.templates import ML_LIMITATION_NOTE, render_text
from medsafe.kb.rules import RULES
from medsafe.models.domain import (Evidence, Explanation, Finding, MedOrder, MlPrediction,
                                   Patient, Prescription)
from fastapi.testclient import TestClient

FIXED_TIME = datetime(2026, 9, 30, tzinfo=timezone.utc)


def _prescription():
    return Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Combiflam")]),
        new_orders=[MedOrder(drug_name="Dolo 650"), MedOrder(drug_name="Warfarin")])


def _fake_predictor(label="Minor", probability=0.87, names=None):
    all_names = {name.casefold() for rule in RULES
        if rule.kind.value == "DDI" and rule.severity.value == "UNSPECIFIED"
        for name in rule.drugs}
    return engine.MlPredictor(lambda _a, _b: (label, probability),
        frozenset(all_names if names is None else names), tau=0.70,
        model_fingerprint="test-fingerprint", reason="Fake predictor for tests.")


def test_ml_note_only_attaches_to_unspecified_ddi_and_preserves_findings():
    off = engine.MlPredictor(None, frozenset(), state="NOT_AVAILABLE", reason="Forced off.")
    report_off = engine.analyze(_prescription(), clock=lambda: FIXED_TIME, ml_predictor=off)
    report_on = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                               ml_predictor=_fake_predictor())
    signature = lambda report: [(f.type, f.severity, f.rule_id) for f in report.findings]
    assert signature(report_on) == signature(report_off)
    assert [f.recommendation for f in report_on.findings] == [
        f.recommendation for f in report_off.findings]
    assert report_on.overall_statement == report_off.overall_statement
    estimates = [f for f in report_on.findings if f.ml_prediction is not None]
    assert estimates and all(f.type.value == "DDI" and f.severity.value == "UNSPECIFIED"
                             for f in estimates)
    assert all(f.explanation and f.explanation.ml_note for f in estimates)
    assert all(f.ml_prediction is None for f in report_on.findings if f not in estimates)
    note = estimates[0].explanation.ml_note
    assert "does not lower the need for review" in note
    assert all(word not in note.casefold() for word in
        ("safe", "low risk", "harmless", "negligible", "ignore", "no risk", "approved", "fine"))
    assert "does not mean" in report_on.overall_statement
    assert all(word not in report_on.overall_statement.casefold()
               for word in ("safe to use", "no risk", "approved"))
    text = render_text(report_on)
    assert "1 finding(s) carry an unverified ML estimate; these are not database classifications." in text
    assert "ML estimate: ENABLED" in text
    assert "  ML-PREDICTED (unverified): Experimental ML estimate (unverified, not a database classification): possibly" in text
    assert "probability" not in text
    assert "Pharmacist review is still required." in text


def test_major_ml_estimate_withheld_and_other_labels_unchanged(monkeypatch):
    predictor = _fake_predictor(label="Major", probability=0.91)
    report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                            ml_predictor=predictor)
    assert all(f.ml_prediction is None for f in report.findings)
    assert "1 MAJOR_WITHHELD" in report.ml_status.reason
    status_line = render_text(report).split("- ML estimate:", 1)[1].splitlines()[0]
    assert "estimate withheld pending outside review" in status_line
    assert "Major" not in status_line
    assert all("Major" not in (f.explanation.ml_note or "") for f in report.findings)
    payload = report.model_dump_json()
    assert '"predicted_label":"Major"' not in payload

    for label in ("Moderate", "Minor"):
        report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                                ml_predictor=_fake_predictor(label=label))
        assert any(f.ml_prediction and f.ml_prediction.predicted_label == label
                   for f in report.findings)

    monkeypatch.setattr(engine, "WITHHOLD_MAJOR_ESTIMATES", False)
    policy_off = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                                ml_predictor=predictor)
    signature = lambda result: [(f.type, f.severity, f.rule_id) for f in result.findings]
    monkeypatch.setattr(engine, "WITHHOLD_MAJOR_ESTIMATES", True)
    policy_on = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                               ml_predictor=predictor)
    assert signature(policy_on) == signature(policy_off)
    assert any(f.severity.value == "MAJOR" and "warfarin + ibuprofen" in f.reason
               for f in policy_on.findings)


def test_api_json_omits_withheld_major_class(monkeypatch):
    from medsafe.api.app import app
    monkeypatch.setattr(engine, "_load_ml_predictor", lambda: _fake_predictor(label="Major"))
    response = TestClient(app).post("/analyze", json={
        "patient": {"current_meds": [{"drug_name": "acetaminophen"}]},
        "new_orders": [{"drug_name": "potassium chloride"}]})
    assert response.status_code == 200
    payload = response.json()
    assert "estimate withheld pending outside review" in payload["ml_status"]["reason"]
    assert all(not item.get("ml_prediction") for item in payload["findings"])
    assert "predicted_label" not in response.text
    assert "MAJOR_WITHHELD" not in response.text
    assert "Major" not in response.text


def test_ml_unavailable_report_has_no_note_or_header_estimate_sentence():
    unavailable = engine.MlPredictor(None, frozenset(), state="NOT_AVAILABLE",
                                     reason="Test unavailable.")
    report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                            ml_predictor=unavailable)
    assert all(f.ml_prediction is None for f in report.findings)
    assert all(f.explanation.ml_note is None for f in report.findings)
    text = render_text(report)
    assert "ML estimate: NOT_AVAILABLE (Test unavailable." in text
    assert "pairs already have source classifications" in text
    assert "finding(s) carry an unverified ML estimate" not in text


def test_fixed_ml_limitation_note_appears_once_only_when_estimates_exist():
    on = engine.analyze(_prescription(), ml_predictor=_fake_predictor())
    off = engine.analyze(_prescription(), ml_predictor=engine.MlPredictor(
        None, frozenset(), state="NOT_AVAILABLE", reason="Test unavailable."))
    assert render_text(on).count(ML_LIMITATION_NOTE) == 1
    assert ML_LIMITATION_NOTE not in render_text(off)
    assert not any(term in ML_LIMITATION_NOTE.casefold()
                   for term in ("safe", "no risk", "approved"))


def test_predictor_none_or_exception_does_not_block_checks():
    for fn in (lambda _a, _b: None,
               lambda _a, _b: (_ for _ in ()).throw(RuntimeError("predictor failure"))):
        base = _fake_predictor()
        context = engine.MlPredictor(fn, base.drug_names, tau=0.7)
        report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME, ml_predictor=context)
        assert report.findings and report.ml_status is not None
        assert all(f.ml_prediction is None for f in report.findings)
        if report.ml_status.state == "NOT_AVAILABLE":
            assert "predictor failure" in report.ml_status.reason


def test_missing_rule_drug_name_records_reason_and_attaches_nothing():
    report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
                            ml_predictor=_fake_predictor(names=set()))
    assert all(f.ml_prediction is None for f in report.findings)
    assert report.ml_status.state == "ENABLED"
    assert "UNKNOWN_DRUG" in report.ml_status.reason

def test_ml_abstention_causes_are_distinct_in_status():
    names = _fake_predictor().drug_names
    report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
        ml_predictor=engine.MlPredictor(lambda _a, _b: None, names, reason="test"))
    assert "PAIR_ALREADY_LABELED" in report.ml_status.reason
    assert "BELOW_THRESHOLD" in report.ml_status.reason
    missing = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
        ml_predictor=engine.MlPredictor(lambda _a, _b: None, frozenset(), reason="test"))
    assert "UNKNOWN_DRUG" in missing.ml_status.reason
    disabled = engine.analyze(_prescription(), clock=lambda: FIXED_TIME,
        ml_predictor=engine.MlPredictor(None, frozenset(), state="DISABLED_BY_GATE", reason="off"))
    assert "MODEL_DISABLED" in disabled.ml_status.reason


def test_ml_status_renders_each_abstention_reason_in_plain_language():
    names = _fake_predictor().drug_names
    cases = [
        (engine.MlPredictor(lambda _a, _b: None, frozenset(), reason="test"),
         "drug absent from model data"),
        (engine.MlPredictor(lambda _a, _b: None, names, reason="test",
            listed_pairs=frozenset(), unlabeled_pairs=frozenset()),
         "pair not listed by DDInter"),
        (engine.MlPredictor(lambda _a, _b: None, names, reason="test"),
         "pair below model threshold"),
    ]
    for predictor, expected in cases:
        report = engine.analyze(_prescription(), ml_predictor=predictor)
        text = render_text(report)
        status = next(line for line in text.splitlines() if line.startswith("- ML estimate:"))
        assert expected in status
        assert not any(code in status for code in (
            "UNKNOWN_DRUG", "PAIR_NOT_LISTED", "PAIR_ALREADY_LABELED",
            "BELOW_THRESHOLD", "MODEL_DISABLED"))
    labeled = engine.analyze(_prescription(), ml_predictor=cases[2][0])
    status = next(line for line in render_text(labeled).splitlines()
                  if line.startswith("- ML estimate:"))
    assert "source classifications" in status


def test_default_loader_handles_missing_dependency_and_bad_hash(monkeypatch):
    monkeypatch.setattr(engine, "_import_ml_modules", lambda: (_ for _ in ()).throw(
        ModuleNotFoundError("scikit-learn missing")))
    missing = engine._load_ml_predictor()
    assert missing.state == "NOT_AVAILABLE" and "ModuleNotFoundError" in missing.reason
    monkeypatch.setattr(engine, "_import_ml_modules", lambda: (_ for _ in ()).throw(
        ValueError("SHA-256 mismatch for severity_model.joblib")))
    tampered = engine._load_ml_predictor()
    assert tampered.state == "NOT_AVAILABLE" and "SHA-256 mismatch" in tampered.reason


def test_default_loader_reports_gate_disabled(monkeypatch):
    monkeypatch.setattr(engine, "_read_ml_manifest", lambda: {
        "model_name": "fake", "seed": 1, "files": {}})
    monkeypatch.setattr(engine, "_import_ml_modules", lambda: (
        lambda: SimpleNamespace(enabled=False, vectors=SimpleNamespace(vectors={}), tau=1.01,
                                 listed_pairs=frozenset(), unlabeled_pairs=frozenset()),
        lambda *_args: None))
    assert engine._load_ml_predictor().state == "DISABLED_BY_GATE"


def test_api_analyze_survives_missing_optional_ml_package_in_subprocess():
    code = '''
import importlib.abc, sys
class BlockML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "medsafe.ml" or fullname.startswith("medsafe.ml."):
            raise ModuleNotFoundError("optional ML dependencies missing")
sys.meta_path.insert(0, BlockML())
from medsafe.api.app import analyze_structured
from medsafe.models.domain import Patient, Prescription
result = analyze_structured(Prescription(patient=Patient()))
assert result.ml_status.state == "NOT_AVAILABLE"
assert "optional ML dependencies missing" in result.ml_status.reason
'''
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).parents[1])


def test_same_input_and_fake_predictor_render_deterministically():
    predictor = _fake_predictor(label="Moderate", probability=0.91)
    first = engine.analyze(_prescription(), clock=lambda: FIXED_TIME, ml_predictor=predictor)
    second = engine.analyze(_prescription(), clock=lambda: FIXED_TIME, ml_predictor=predictor)
    assert first.model_dump() == second.model_dump()


def test_real_artifact_integration_when_ml_extra_is_installed():
    import pytest
    for package in ("numpy", "scipy", "sklearn", "joblib", "pandas"):
        pytest.importorskip(package)
    report = engine.analyze(_prescription(), clock=lambda: FIXED_TIME)
    assert report.ml_status.state in {"ENABLED", "DISABLED_BY_GATE", "NOT_AVAILABLE"}
    if report.ml_status.state == "ENABLED":
        import json
        from medsafe.ml.predict import MODEL_DIR
        manifest = json.loads((MODEL_DIR / "manifest.json").read_text(encoding="utf-8"))
        assert report.ml_status.model_fingerprint == manifest["files"]["severity_model.joblib"]["sha256"]
        assert report.ml_status.tau == manifest["tau"]
    assert all(f.ml_prediction is None or
               (f.type.value == "DDI" and f.severity.value == "UNSPECIFIED")
               for f in report.findings)


def test_additive_ml_schema_fields_have_legacy_compatible_defaults():
    rule = next(item for item in RULES if item.kind.value == "DDI")
    finding = Finding(type=rule.kind, severity=rule.severity, drugs_involved=list(rule.drugs),
        reason=rule.reason, mechanism=rule.mechanism, recommendation=rule.recommendation,
        rule_id=rule.rule_id, evidence=rule.evidence)
    explanation = Explanation(headline="h", risk="r", why="w", trigger="t",
        recommendation="r", source="s", review_label="Not reviewed", rule_id=rule.rule_id)
    report = SafetyReport(findings=[finding])
    assert finding.model_dump()["ml_prediction"] is None
    assert explanation.model_dump()["ml_note"] is None
    assert report.model_dump()["ml_status"] is None
    assert MlPrediction().label_status == "ML-PREDICTED, unverified"
