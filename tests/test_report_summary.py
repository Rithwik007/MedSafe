import json

from fastapi.testclient import TestClient

from medsafe.api.app import app
from medsafe.checkers.engine import analyze
from medsafe.core.report import SafetyReport
from medsafe.llm.report_summary import aggregate_facts, guard_report_summary
from medsafe.models.domain import Patient, Prescription


class FakeClient:
    def __init__(self, output):
        self.output = output
        self.prompt = None

    def complete(self, system, prompt):
        self.prompt = (system, prompt)
        return json.dumps(self.output)


def report():
    return analyze(Prescription(patient=Patient(), new_orders=[]))


def test_aggregate_summary_contains_only_counts_and_checker_states():
    value = report()
    facts = aggregate_facts(value)
    encoded = json.dumps(facts)
    assert "severity_counts" in encoded
    assert "unresolved_item_count" in encoded
    assert all("name" in checker and "status" in checker for checker in facts["checkers"])


def test_report_summary_guard_requires_supported_severity_count_and_rejects_medical_advice():
    facts = {"checkers": [{"name": "DDI", "status": "RAN", "rules_loaded": 3}],
             "checker_status_counts": {"RAN": 1}, "finding_count": 1,
             "severity_counts": {"MAJOR": 1}, "finding_type_counts": {},
             "unresolved_item_count": 0, "suggested_match_count": 0}
    good = {"what_ran": "DDI RAN, 1 RAN.",
            "what_it_found": "1 MAJOR finding.",
            "issues": "0 unresolved items and 0 suggested matches.",
            "takeaway": "Review the finding using the provided details."}
    assert guard_report_summary(json.dumps(good), facts) == good
    bad = {**good, "takeaway": "This is safe to use."}
    assert guard_report_summary(json.dumps(bad), facts) is None
    missing = {**good, "what_it_found": "A MAJOR finding."}
    assert guard_report_summary(json.dumps(missing), facts) is None


def test_report_summary_provider_gets_aggregate_facts_only():
    from medsafe.llm.report_summary import generate_report_summary
    value = report()
    facts = aggregate_facts(value)
    checker_text = ", ".join(f"{item['name']} {item['status']}" for item in facts["checkers"])
    checker_text += "; " + ", ".join(f"{count} {status}" for status, count in facts["checker_status_counts"].items())
    fake = FakeClient({"what_ran": checker_text,
                       "what_it_found": (f"{facts['finding_count']} findings." if facts["finding_count"] else "No findings were reported."),
                       "issues": f"{facts['unresolved_item_count']} unresolved items and "
                                 f"{facts['suggested_match_count']} suggested matches.",
                       "takeaway": "Review the provided details."})
    summary, _ = generate_report_summary(value, fake)
    assert summary is not None
    sent = json.loads(fake.prompt[1])
    assert set(sent) == {"checkers", "checker_status_counts", "finding_count",
                         "severity_counts", "finding_type_counts",
                         "unresolved_item_count", "suggested_match_count"}
    assert "findings" not in sent and "patient" not in sent


def test_explain_report_endpoint_returns_disabled_state_without_changing_report_schema(monkeypatch):
    monkeypatch.setenv("MEDSAFE_DISABLE_DOTENV", "1")
    monkeypatch.setenv("MEDSAFE_LLM_ENABLED", "0")
    response = TestClient(app).post("/explain-report?use_llm=true", json=SafetyReport().model_dump())
    assert response.status_code == 200
    assert response.json()["state"] == "DISABLED"
    assert response.json()["overview"] is None
    assert "overview" not in SafetyReport.model_fields
