from fastapi.testclient import TestClient
from medsafe.api.app import app
from medsafe.core.normalizer import normalize_drug
from medsafe.models.domain import Patient, MedOrder, Prescription
from medsafe.checkers.engine import analyze
from medsafe.nlp.parser import parse_prescription
from scripts.import_ddinter import import_ddinter
from scripts.export_review_sheet import export_review_sheet
from scripts.apply_review import apply_review
from medsafe.kb.rules import RULES
from scripts.export_review_sheet import export_review_sheet
from scripts.apply_review import apply_review
import csv

client = TestClient(app)


def test_unresolved_name_never_claimed_safe():
    report = analyze(Prescription(patient=Patient(), new_orders=[MedOrder(drug_name="mystery pill")]))
    assert report.findings == []
    assert any("not in curated" in item.reason for item in report.unresolved_items)
    assert "does not mean" in report.overall_statement


def test_exact_normalization_and_unknown():
    assert normalize_drug("metformin 500mg").canonical == "Metformin"
    assert normalize_drug("unknown brand").canonical is None


def test_parser_supported_and_unsupported():
    orders, unresolved = parse_prescription("metformin 500 mg BD; mystery med")
    assert len(orders) == 1 and orders[0].frequency_per_day == 2
    assert len(unresolved) == 1


def test_api_health_and_report():
    assert client.get("/health").json()["clinical_rules_loaded"] == len(RULES)
    response = client.post("/analyze", json={"patient": {"current_meds": [{"drug_name": "warfarin"}]}, "new_orders": [{"drug_name": "ibuprofen"}]})
    assert response.status_code == 200
    assert any(item["type"] == "DDI" for item in response.json()["findings"])
    assert response.json()["unresolved_items"] == []
    assert response.json()["checker_status"]


def test_ddinter_import_filters_maps_and_keeps_provenance(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    sample = raw / "ddinter_downloads_code_A.csv"
    sample.write_text(
        "DDInterID_A,Drug_A,DDInterID_B,Drug_B,Level,Mechanism\n"
        "DDInter1,Drug A,DDInter2,Drug B,Major,Source mechanism\n"
        "DDInter3,Drug A,DDInter4,Drug C,Moderate,\n"
        "DDInter5,Drug B,DDInter6,Drug C,Minor,\n"
        "DDInter7,Drug A,DDInter8,Drug D,Unknown,\n"
        "DDInter9,Outside,DDInter10,Drug A,Major,\n",
        encoding="utf-8",
    )
    whitelist = tmp_path / "drug_whitelist.csv"
    whitelist.write_text("Drug A\nDrug B\nDrug C\nDrug D\n", encoding="utf-8")
    output = tmp_path / "rules.csv"

    result = import_ddinter(raw, whitelist, output)
    rows = list(csv.DictReader(output.open(encoding="utf-8")))

    assert result["imported"] == 4
    assert result["unmapped_levels"] == {}
    assert {row["severity"] for row in rows} == {"MAJOR", "MODERATE", "MINOR", "UNSPECIFIED"}
    major = next(row for row in rows if row["severity"] == "MAJOR")
    assert major["mechanism"] == "Source mechanism"
    assert major["source_url"] == "https://ddinter.scbdd.com/download/"
    assert major["reviewed_by"] == major["verified_on"] == ""


def test_reversed_duplicate_keeps_highest_severity_and_logs_conflict(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "ddinter_downloads_code_A.csv").write_text(
        "DDInterID_A,Drug_A,DDInterID_B,Drug_B,Level\n"
        "DDInter1,Drug A,DDInter2,Drug B,Minor\n"
        "DDInter2,Drug B,DDInter1,Drug A,Contraindicated\n",
        encoding="utf-8",
    )
    whitelist = tmp_path / "whitelist.csv"
    whitelist.write_text("Drug A\nDrug B\n", encoding="utf-8")
    result = import_ddinter(raw, whitelist, tmp_path / "rules.csv")
    rows = list(csv.DictReader((tmp_path / "rules.csv").open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["severity"] == "CONTRAINDICATED"
    assert result["counts"]["severity_conflict_pair_rows"] == 1
    assert result["duplicate_severity_conflicts"][0]["kept_severity"] == "CONTRAINDICATED"


def test_imported_ddinter_rule_emits_sourced_warning():
    report = analyze(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="warfarin")]),
        new_orders=[MedOrder(drug_name="ibuprofen")]))
    warning = next(f for f in report.findings if f.rule_id.startswith("DDINTER-"))
    assert warning.severity.value == "MAJOR"
    assert warning.evidence.source_url == "https://ddinter.scbdd.com/download/"
    assert "not_independently_clinically_reviewed" in warning.evidence.review_status
    assert warning.evidence.review_label == "Not reviewed"


def test_unspecified_ddinter_rule_emits_review_warning_below_moderate():
    from medsafe.kb.rules import RULES
    from medsafe.models.domain import Severity

    rule = next(rule for rule in RULES if rule.severity == Severity.UNSPECIFIED)
    a, b = rule.drugs
    report = analyze(Prescription(patient=Patient(current_meds=[MedOrder(drug_name=a)]),
        new_orders=[MedOrder(drug_name=b)]))
    warning = next(f for f in report.findings if f.rule_id == rule.rule_id)
    assert warning.severity == Severity.UNSPECIFIED
    assert warning.reason.startswith("Interaction reported by DDInter without a severity classification; requires pharmacist review.")
    assert "pharmacist review" in warning.recommendation.lower()
    assert warning in report.findings


def test_unspecified_findings_sort_after_moderate():
    from medsafe.kb.rules import RULES
    from medsafe.models.domain import Severity

    unspecified = next(rule for rule in RULES if rule.severity == Severity.UNSPECIFIED)
    moderate = next(rule for rule in RULES if rule.severity == Severity.MODERATE)
    report = analyze(Prescription(
        patient=Patient(current_meds=[MedOrder(drug_name=unspecified.drugs[0]), MedOrder(drug_name=moderate.drugs[0])]),
        new_orders=[MedOrder(drug_name=unspecified.drugs[1]), MedOrder(drug_name=moderate.drugs[1])]))
    ids = [finding.rule_id for finding in report.findings]
    assert ids.index(moderate.rule_id) < ids.index(unspecified.rule_id)


def test_review_sheet_applies_only_complete_major_review(tmp_path):
    rules = tmp_path / "rules.csv"
    rules.write_text(
        "rule_id,type,drugs,severity,reason,mechanism,recommendation,source_name,source_url,version_or_access_date,review_status,reviewed_by,verified_on,trigger,license\n"
        "r1,DDI,A|B,MAJOR,reason,,,DDInter,https://source.test/r1,date,dataset_imported_not_independently_clinically_reviewed,,,,CC BY-NC-SA 4.0\n"
        "r2,DDI,C|D,MODERATE,reason,,,DDInter,https://source.test/r2,date,dataset_imported_not_independently_clinically_reviewed,,,,CC BY-NC-SA 4.0\n",
        encoding="utf-8",
    )
    sheet = tmp_path / "major_rules_review.csv"
    assert export_review_sheet(rules, sheet) == 1
    with sheet.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[0].update(mechanism="Source checked", recommendation="Review source", reviewer="Reviewer", verified_on="2026-09-30")
    with sheet.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    assert apply_review(rules, sheet) == 1
    updated = list(csv.DictReader(rules.open(encoding="utf-8", newline="")))
    assert updated[0]["review_status"] == "reviewed"
    assert updated[0]["reviewed_by"] == "Reviewer"
    assert updated[1]["review_status"] != "reviewed"


def test_graph_class_rule_matches_two_members_from_seed(tmp_path):
    from medsafe.kb.graph import KnowledgeGraph

    classes = tmp_path / "drug_classes.csv"
    classes.write_text("drug,atc_code,class,source\nDrug A,X01,Demo class,fixture\nDrug B,X01,Demo class,fixture\n", encoding="utf-8")
    rules = tmp_path / "rules.csv"
    rules.write_text("rule_id,type,drugs,severity,reason,source_url\n", encoding="utf-8")
    class_rules = tmp_path / "class_rules.csv"
    class_rules.write_text("rule_id,class_a,class_b,severity,reason,source_url\nCR1,Demo class,Demo class,MAJOR,fixture,https://fixture.test\n", encoding="utf-8")
    graph = KnowledgeGraph.load(classes, rules, class_rules)
    assert graph.get_class("Drug A") == ("Demo class",)
    assert graph.matching_class_rules("Drug A", "Drug B")[0]["rule_id"] == "CR1"


def test_review_sheet_exports_and_applies_only_complete_review(tmp_path):
    rules = tmp_path / "rules.csv"
    rules.write_text(
        "rule_id,type,drugs,severity,reason,mechanism,recommendation,source_name,source_url,version_or_access_date,review_status,reviewed_by,verified_on,trigger,license\n"
        "r1,DDI,A|B,MAJOR,reason,,,DDInter,https://source.test/r1,date,dataset_imported_not_independently_clinically_reviewed,,,,CC BY-NC-SA 4.0\n"
        "r2,DDI,C|D,MODERATE,reason,,,DDInter,https://source.test/r2,date,dataset_imported_not_independently_clinically_reviewed,,,,CC BY-NC-SA 4.0\n",
        encoding="utf-8",
    )
    sheet = tmp_path / "major_rules_review.csv"
    assert export_review_sheet(rules, sheet) == 1
    with sheet.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["source_url"] == "https://source.test/r1"
    rows[0].update(mechanism="Verified mechanism", recommendation="Review clinically", reviewer="Reviewer", verified_on="2026-09-30")
    with sheet.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    assert apply_review(rules, sheet) == 1
    updated = list(csv.DictReader(rules.open(encoding="utf-8", newline="")))
    assert updated[0]["review_status"] == "reviewed"
    assert updated[0]["reviewed_by"] == "Reviewer"
    assert updated[1]["review_status"] != "reviewed"
