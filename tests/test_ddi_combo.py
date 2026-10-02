from dataclasses import replace

from medsafe.checkers.ddi import check_ddi
from medsafe.kb.rules import RULES
from medsafe.models.domain import MedOrder, Patient, Prescription, Severity


def test_combination_ingredient_triggers_real_warfarin_ddi_rule():
    report = check_ddi(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Combiflam")]),
        new_orders=[MedOrder(drug_name="Warfarin")]))
    source_rule = next(rule for rule in RULES if set(rule.drugs) == {"Warfarin", "Ibuprofen"})
    warning = next(item for item in report if item.rule_id == source_rule.rule_id)
    assert warning.severity == Severity.MAJOR
    assert warning.drugs_involved == ["Combiflam", "Warfarin"]
    assert "warfarin + ibuprofen" in warning.reason
    assert warning.evidence.review_label == "Not reviewed"


def test_duplicate_combo_ddi_pair_collapses_and_lists_all_orders():
    report = check_ddi(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Warfarin")]),
        new_orders=[MedOrder(drug_name="Combiflam"), MedOrder(drug_name="Ibuprofen")]))
    target_rule = next(rule for rule in RULES if set(rule.drugs) == {"Warfarin", "Ibuprofen"})
    relevant = [item for item in report if item.rule_id == target_rule.rule_id]
    assert len(relevant) == 1
    assert set(relevant[0].drugs_involved) == {"Warfarin", "Combiflam", "Ibuprofen"}


def test_reversed_ddi_rule_pair_emits_one_warning_and_keeps_highest_severity():
    original = next(rule for rule in RULES if set(rule.drugs) == {"Warfarin", "Ibuprofen"})
    reversed_lower = replace(original, rule_id="REVERSED-LOWER", drugs=tuple(reversed(original.drugs)),
                             severity=Severity.MODERATE)
    report = check_ddi(Prescription(patient=Patient(current_meds=[MedOrder(drug_name="Warfarin")]),
        new_orders=[MedOrder(drug_name="Combiflam")]), rules=(original, reversed_lower))
    assert len(report) == 1
    assert report[0].rule_id == original.rule_id
    assert report[0].severity == Severity.MAJOR
