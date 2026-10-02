import csv
from itertools import combinations
from pathlib import Path

from medsafe.checkers.duplicate import check_duplicates
from medsafe.models.domain import MedOrder, Patient, Prescription, Severity

ROOT = Path(__file__).resolve().parents[1]


def prescription(current=(), new=()):
    return Prescription(patient=Patient(current_meds=[MedOrder(drug_name=name) for name in current]),
                        new_orders=[MedOrder(drug_name=name) for name in new])


def test_combiflam_and_dolo_650_report_paracetamol_duplicate():
    report = check_duplicates(prescription(current=("Combiflam",), new=("Dolo 650",)))
    warning = next(item for item in report.findings if item.rule_id.endswith("INGREDIENT"))
    assert warning.severity == Severity.MODERATE
    assert "paracetamol appears in Combiflam and in Dolo 650." in warning.reason
    assert "Orders involved:" in warning.reason
    assert warning.drugs_involved == ["Combiflam", "Dolo 650"]
    assert warning.evidence.source_name == "duplicate_policy.csv"
    assert warning.evidence.review_status == "DESIGN_DECISION"
    assert "ATC-CLASS" not in [item.rule_id for item in report.findings]


def test_same_generic_in_current_and_new_orders_reports_duplicate():
    report = check_duplicates(prescription(current=("Metformin",), new=("metformin 500mg",)))
    assert len(report.findings) == 1
    assert report.findings[0].rule_id.endswith("INGREDIENT")
    assert report.findings[0].drugs_involved == ["Metformin", "metformin 500mg"]


def test_real_shared_atc_code_reports_class_duplicate():
    with (ROOT / "data/seed/drug_classes.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    entries = []
    for row in rows:
        if row["class"] == "TODO_VERIFY":
            continue
        codes = {code.strip()[:5] for code in row["atc_code"].split("|") if len(code.strip()) >= 5}
        entries.append((row["drug"], codes))
    first, second = next((a, b) for a, b in combinations(entries, 2)
                         if a[0].casefold() != b[0].casefold() and a[1] & b[1])
    shared_code = sorted(first[1] & second[1])[0]
    report = check_duplicates(prescription(current=(first[0],), new=(second[0],)))
    warning = next(item for item in report.findings if item.rule_id.endswith("ATC-CLASS"))
    assert shared_code in warning.reason
    assert "Confirm both orders are intended" in warning.recommendation
    assert warning.evidence.rationale == "project design choice, not a clinical rule"


def test_unrelated_drugs_do_not_report_duplicate():
    report = check_duplicates(prescription(current=("Metformin",), new=("Warfarin",)))
    assert report.findings == []


def test_single_order_never_compares_with_itself():
    report = check_duplicates(prescription(new=("Combiflam",)))
    assert report.findings == []


def test_todo_verify_atc_is_skipped():
    report = check_duplicates(prescription(current=("Acetylsalicylic acid",), new=("Clopidogrel",)))
    assert not any(item.rule_id.endswith("ATC-CLASS") for item in report.findings)


def test_empty_current_meds_still_checks_new_orders_only():
    report = check_duplicates(prescription(new=("Metformin", "Warfarin")))
    assert report.findings == []


def test_unresolved_drug_is_reported_and_does_not_crash():
    report = check_duplicates(prescription(current=("mystery medicine xyz",), new=("Metformin",)))
    assert any(item.item == "mystery medicine xyz" for item in report.unresolved_items)
    assert report.findings == []


def test_duplicate_recommendation_rationale_and_orders_label():
    warning = check_duplicates(prescription(current=("Combiflam",), new=("Dolo 650",))).findings[0]
    assert warning.recommendation == (
        "Confirm both orders are intended. Ask the prescriber or pharmacist to check the "
        "combined daily amount of the shared ingredient.")
    assert warning.evidence.rationale == "project design choice, not a clinical rule"
    assert "Patient factors:" not in warning.reason
    assert "Orders involved:" in warning.reason


def test_canonical_paracetamol_display_across_combo_scenario():
    import csv
    from pathlib import Path
    from medsafe.checkers.engine import analyze

    report = analyze(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Combiflam")]),
        new_orders=[MedOrder(drug_name="Dolo 650"), MedOrder(drug_name="Warfarin")]))
    with (Path(__file__).parents[1] / "data/seed/ingredient_names.csv").open(
            encoding="utf-8", newline="") as stream:
        display_names = {row["display_name"] for row in csv.DictReader(stream)}
    for finding in report.findings:
        assert "Acetaminophen" not in finding.reason
        if "Ingredient pair:" in finding.reason:
            pair = finding.reason.split("Ingredient pair: ", 1)[1].split(".", 1)[0]
            assert all(name.strip() in display_names for name in pair.split(" + "))
    assert report.findings
    assert any("paracetamol" in finding.reason for finding in report.findings)


def test_ddinter_evidence_keeps_source_and_pair_ids():
    from medsafe.checkers.engine import analyze

    report = analyze(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Warfarin")]),
        new_orders=[MedOrder(drug_name="Ibuprofen")]))
    ddi = next(finding for finding in report.findings if finding.type.value == "DDI")
    assert ddi.evidence.source_url == "https://ddinter.scbdd.com/download/"
    assert len(ddi.evidence.ddinter_ids) == 2
