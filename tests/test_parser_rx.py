import csv
from pathlib import Path
from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from medsafe.api.app import app
from medsafe.models.domain import MedOrder
from medsafe.nlp.parser import ParseLimitError, parse_prescription

client = TestClient(app)


@pytest.mark.parametrize("code,times,as_needed,one_time", [
    ("OD", 1, False, False), ("BD", 2, False, False), ("BID", 2, False, False),
    ("TDS", 3, False, False), ("TID", 3, False, False), ("QID", 4, False, False),
    ("HS", 1, False, False), ("Q4H", 6, False, False), ("Q6H", 4, False, False),
    ("Q8H", 3, False, False), ("Q12H", 2, False, False), ("SOS", None, True, False),
    ("PRN", None, True, False), ("STAT", 1, False, True),
])
def test_frequency_codes_load_from_csv(code, times, as_needed, one_time):
    order = parse_prescription(f"Amoxicillin 500mg {code}").orders[0]
    assert order.frequency_code == code
    assert order.frequency_per_day == times
    assert order.as_needed is as_needed
    assert order.one_time is one_time


@pytest.mark.parametrize("token,form,route,assumed", [
    ("tab", "tablet", "oral", True), ("tabs", "tablet", "oral", True),
    ("tablet", "tablet", "oral", True), ("cap", "capsule", "oral", True),
    ("caps", "capsule", "oral", True), ("capsule", "capsule", "oral", True),
    ("syp", "syrup", "oral", True), ("syrup", "syrup", "oral", True),
    ("susp", "suspension", "oral", True), ("suspension", "suspension", "oral", True),
    ("inj", "injection", None, False), ("injection", "injection", None, False),
    ("oint", "ointment", None, False), ("ointment", "ointment", None, False),
    ("cream", "cream", None, False), ("drops", "drops", None, False),
])
def test_dosage_form_tokens_load_from_csv(token, form, route, assumed):
    order = parse_prescription(f"{token} Amoxicillin 500mg BD").orders[0]
    assert (order.form, order.route, order.route_is_assumed) == (form, route, assumed)


@pytest.mark.parametrize("unit,expected,kind", [
    ("mg", "mg", "MASS"), ("g", "g", "MASS"), ("mcg", "mcg", "MASS"),
    ("ug", "mcg", "MASS"), ("µg", "mcg", "MASS"), ("ml", "ml", "VOLUME"),
    ("iu", "iu", "IU"),
])
def test_units_load_from_csv_without_value_conversion(unit, expected, kind):
    order = parse_prescription(f"Amoxicillin 5 {unit} BD").orders[0]
    assert order.dose_value == 5
    assert order.dose_unit == expected
    assert order.unit_kind == kind


@pytest.mark.parametrize("duration,days", [
    ("x5 days", 5), ("x 5 d", 5), ("for 5 days", 5), ("5d", 5),
    ("for 1 week", 7), ("x2 weeks", 14),
])
def test_supported_duration_forms(duration, days):
    order = parse_prescription(f"Amoxicillin 500mg BD {duration}").orders[0]
    assert order.duration_days == days


@pytest.mark.parametrize("route", ["po", "oral", "iv", "im", "sc", "topical"])
def test_explicit_routes_override_form_assumption(route):
    order = parse_prescription(f"Tab Amoxicillin 500mg BD {route}").orders[0]
    assert order.route == ("oral" if route in {"po", "oral"} else route)
    assert order.route_is_assumed is False


def test_brand_with_strength_number_is_exactly_resolved_but_not_strength():
    augmentin = parse_prescription("Tab Augmentin 625 mg BD x5 days").orders[0]
    assert augmentin.name_used == "Augmentin 625 mg"
    assert augmentin.dose_value is None and augmentin.dose_unit is None
    assert augmentin.frequency_per_day == 2 and augmentin.duration_days == 5
    assert augmentin.parse_confidence == "HIGH"


def test_crocin_advance_strength_brand_resolves_exactly():
    parsed = parse_prescription("Crocin Advance 500mg BD")
    assert len(parsed.orders_for_checking) == 1
    assert parsed.orders[0].name_used == "Crocin Advance 500mg"
    assert parsed.orders[0].dose_value is None


def test_crocin_500mg_stays_unresolved_and_keeps_strength():
    parsed = parse_prescription("Crocin 500mg BD")
    assert parsed.orders_for_checking == []
    assert parsed.orders[0].drug_name == "Crocin"
    assert parsed.orders[0].dose_value == 500
    assert parsed.orders[0].dose_unit == "mg"


def test_tab_crocin_500mg_tds_stays_unresolved():
    order = parse_prescription("Tab Crocin 500mg TDS").orders[0]
    assert order not in parse_prescription("Tab Crocin 500mg TDS").orders_for_checking


def test_bare_dolo_stays_unresolved():
    assert parse_prescription("Tab Dolo").orders_for_checking == []


def test_bare_number_is_not_assumed_to_be_mg():
    order = parse_prescription("Amoxicillin 500 BD").orders[0]
    assert order.dose_value is None and order.dose_unit is None
    assert any("ambiguous" in note for note in order.parse_notes)
    assert order.parse_confidence == "MEDIUM"


def test_quantity_per_intake_is_explicit_only():
    order = parse_prescription("Cap Amoxicillin 500mg 2 caps TDS").orders[0]
    assert order.units_per_intake == 2
    assert order.form == "capsule"


def test_quantity_is_never_defaulted_to_one():
    order = parse_prescription("Tab Amoxicillin 500mg BD").orders[0]
    assert order.units_per_intake is None
    assert "quantity per intake not stated" in order.parse_notes


def test_slots_count_nonzero_times_and_quantities():
    order = parse_prescription("Cap Amoxicillin 500mg 1-0-1").orders[0]
    assert order.frequency_per_day == 2
    assert order.units_per_intake == 1


@pytest.mark.parametrize("pattern,times,units", [
    ("1-1-1", 3, 1), ("0-0-1", 1, 1), ("2-0-2", 2, 2),
])
def test_additional_slot_patterns(pattern, times, units):
    order = parse_prescription(f"Amoxicillin 500mg {pattern}").orders[0]
    assert order.frequency_per_day == times
    assert order.units_per_intake == units


def test_unequal_slot_values_leave_frequency_and_units_unresolved():
    order = parse_prescription("Amoxicillin 500mg 1-0-2").orders[0]
    assert order.frequency_per_day is None
    assert order.units_per_intake is None
    assert any("unequal" in note for note in order.parse_notes)


def test_fractional_slot_value_is_unresolved():
    order = parse_prescription("Amoxicillin 500mg 1.5-0-1").orders[0]
    assert order.frequency_per_day is None
    assert any("non-whole" in note for note in order.parse_notes)


def test_quantity_conflict_is_not_guessed():
    order = parse_prescription("Amoxicillin 500mg 2 caps 1-0-1").orders[0]
    assert order.units_per_intake is None
    assert any("conflict" in note for note in order.parse_notes)


def test_month_duration_is_not_supported_and_is_retained():
    order = parse_prescription("Amoxicillin 500mg BD for 2 months").orders[0]
    assert order.duration_days is None
    assert any("Months are not supported" in note for note in order.parse_notes)
    assert "months" in order.unparsed_tokens


def test_ibuprofen_bare_400_scheduled_and_sos_is_unknown_maximum():
    order = parse_prescription("Tab Ibuprofen 400 TDS SOS").orders[0]
    assert order.dose_value is None and order.dose_unit is None
    assert any("ambiguous" in note for note in order.parse_notes)
    assert order.frequency_per_day is None and order.as_needed is True
    assert order.unparsed_tokens == []
    assert any("Conflicting frequency tokens (TDS and SOS)" in note for note in order.parse_notes)


@pytest.mark.parametrize("text,code", [
    ("Tab Ibuprofen 400 TDS SOS", "TDS SOS"),
    ("Tab Ibuprofen 400 SOS TDS", "SOS TDS"),
    ("Tab Ibuprofen 400 PRN OD", "PRN OD"),
])
def test_scheduled_and_as_needed_frequency_conflict(text, code):
    order = parse_prescription(text).orders[0]
    assert order.frequency_code == code
    assert order.frequency_per_day is None and order.as_needed is True
    assert order.unparsed_tokens == []
    assert order.parse_confidence != "HIGH"


def test_distinct_scheduled_frequency_codes_are_unresolved():
    order = parse_prescription("Tab Metformin 500 mg BD TDS").orders[0]
    assert order.frequency_code is None and order.frequency_per_day is None
    assert order.as_needed is False and order.parse_confidence == "LOW"
    assert order.unparsed_tokens == []
    assert any("Conflicting scheduled frequency codes (BD, TDS)" in note for note in order.parse_notes)


def test_repeated_scheduled_code_is_not_a_conflict():
    order = parse_prescription("Tab Metformin 500 mg TDS TDS").orders[0]
    assert order.frequency_code == "TDS" and order.frequency_per_day == 3
    assert not any("Conflicting" in note for note in order.parse_notes)


def test_slot_pattern_and_disagreeing_frequency_code_are_unresolved():
    order = parse_prescription("Tab Paracetamol 500 mg 1-0-1 TDS").orders[0]
    assert order.frequency_code is None and order.frequency_per_day is None
    assert any("Conflicting scheduled frequency codes (1-0-1, TDS)" in note
               for note in order.parse_notes)


def test_slot_pattern_and_matching_frequency_code_agree_by_daily_count():
    # 1-0-1 means two daily administrations; BD also means two, so no conflict.
    order = parse_prescription("Tab Paracetamol 500 mg 1-0-1 BD").orders[0]
    assert order.frequency_code == "BD" and order.frequency_per_day == 2
    assert order.units_per_intake == 1


def test_volume_unit_is_not_mass_and_has_conversion_note():
    order = parse_prescription("Syp Paracetamol 5 ml BD").orders[0]
    assert order.dose_value == 5 and order.dose_unit == "ml"
    assert order.unit_kind == "VOLUME"
    assert "Volume stated; concentration (mass per volume) not stated; cannot convert to mass." in order.parse_notes


def test_mass_and_iu_units_have_distinct_kinds():
    warfarin = parse_prescription("Tab Warfarin 5 mg OD").orders[0]
    heparin = parse_prescription("Inj Heparin 5000 iu").orders[0]
    assert warfarin.dose_unit == "mg" and warfarin.unit_kind == "MASS"
    assert heparin.dose_unit == "iu" and heparin.unit_kind == "IU"


def test_injection_ceftriaxone_does_not_assume_route():
    order = parse_prescription("Inj Ceftriaxone 1 g OD").orders[0]
    assert order.route is None and order.route_is_assumed is False
    assert order not in parse_prescription("Inj Ceftriaxone 1 g OD").orders_for_checking


def test_blue_one_line_is_unresolved_candidate_not_unparsed_line():
    parsed = parse_prescription("take the blue one daily")
    assert parsed.unparsed_lines == []
    assert parsed.orders and parsed.orders_for_checking == []
    assert any("no medication checks applied" in note for note in parsed.orders[0].parse_notes)


def test_metformin_after_food_remains_leftover():
    order = parse_prescription("Tab Metformin 500 mg BD after food").orders[0]
    assert order.unparsed_tokens == ["after", "food"]


def test_hs_note_is_kept():
    order = parse_prescription("Amoxicillin 500mg HS").orders[0]
    assert "at bedtime" in order.parse_notes


def test_strength_and_route_can_be_explicit():
    order = parse_prescription("Amoxicillin 250 mcg BD oral").orders[0]
    assert order.dose_value == 250 and order.dose_unit == "mcg"
    assert order.route == "oral" and not order.route_is_assumed


def test_leftover_tokens_are_not_dropped():
    order = parse_prescription("1) Rx Tab Warfarin 5 mg OD after food").orders[0]
    assert order.unparsed_tokens == ["after", "food"]
    assert order.source_line.startswith("1)")


def test_no_name_candidate_becomes_unparsed_line():
    parsed = parse_prescription("Tab 500mg BD")
    assert not parsed.orders
    assert parsed.unparsed_lines[0].line == "Tab 500mg BD"


def test_malformed_text_returns_result_without_raising():
    parsed = parse_prescription("???")
    assert not parsed.orders
    assert parsed.unparsed_lines


def test_empty_input_returns_empty_parse_result():
    parsed = parse_prescription("")
    assert parsed.orders == [] and parsed.unparsed_lines == []


def test_newline_and_semicolon_split_lines():
    parsed = parse_prescription("Amoxicillin 500mg BD\nWarfarin 5mg OD; Metformin 500mg BD")
    assert len(parsed.orders) == 3


def test_comma_splits_only_before_known_form():
    parsed = parse_prescription("Tab Metformin 500mg BD, Cap Amoxicillin 500mg TDS")
    assert len(parsed.orders) == 2
    assert parsed.orders[1].form == "capsule"


def test_comma_without_known_form_stays_in_same_line_as_leftover():
    parsed = parse_prescription("Amoxicillin 500mg BD, after food")
    assert len(parsed.orders) == 1
    assert "after" in parsed.orders[0].unparsed_tokens


def test_list_marker_and_leading_rx_are_stripped_for_parsing():
    order = parse_prescription("1) Rx Tab Amoxicillin 500mg BD").orders[0]
    assert order.drug_name == "Amoxicillin"


@pytest.mark.parametrize("marker", ["1)", "1.", "-", "•"])
def test_all_list_marker_forms_are_stripped(marker):
    order = parse_prescription(f"{marker} Tab Amoxicillin 500mg BD").orders[0]
    assert order.drug_name == "Amoxicillin"


def test_strength_bearing_brand_number_is_not_double_counted():
    order = parse_prescription("Dolo 650").orders[0]
    assert order.name_used == "Dolo 650"
    assert order.dose_value is None


def test_candidate_keeps_multiple_words():
    order = parse_prescription("Crocin Advance 500mg BD").orders[0]
    assert order.drug_name == "Crocin Advance 500mg"
    assert order.name_used == "Crocin Advance 500mg"


def test_parse_confidence_high_for_complete_source_line():
    order = parse_prescription("Cap Amoxicillin 500mg 1-0-1").orders[0]
    assert order.parse_confidence == "HIGH"


def test_parse_confidence_medium_for_resolved_frequency_without_strength():
    order = parse_prescription("Amoxicillin BD").orders[0]
    assert order.parse_confidence == "MEDIUM"


def test_parse_confidence_low_when_frequency_missing():
    order = parse_prescription("Amoxicillin 500mg").orders[0]
    assert order.parse_confidence == "LOW"


def test_legacy_unpacking_returns_old_pair_shape():
    orders, unresolved = parse_prescription("metformin 500 mg BD; mystery med")
    assert len(orders) == 1
    assert len(unresolved) == 1
    assert unresolved[0].item == "mystery med"
    assert "parsed fields retained" in unresolved[0].reason


@pytest.mark.parametrize("text,part", [
    ("x" * 5001, "5000 characters"),
    ("\n".join("Amoxicillin" for _ in range(51)), "50 lines"),
    ("A" * 301, "300 characters"),
])
def test_parser_input_limits_raise_clear_error(text, part):
    with pytest.raises(ParseLimitError, match=part):
        parse_prescription(text)


def test_text_api_maps_input_limit_to_http_422():
    response = client.post("/analyze-text", json={"patient": {}, "prescription_text": "x" * 5001})
    assert response.status_code == 422
    assert "5000 characters" in response.json()["detail"]


def test_text_api_surfaces_unparsed_tokens_and_parser_notes():
    response = client.post("/analyze-text", json={"patient": {},
        "prescription_text": "Tab Amoxicillin 500mg BD after food"})
    assert response.status_code == 200
    reasons = [item["reason"] for item in response.json()["unresolved_items"]]
    assert any("Unparsed token: after" in reason for reason in reasons)


def test_text_api_preserves_unresolved_parsed_order_fields():
    response = client.post("/analyze-text", json={"patient": {}, "prescription_text": "Crocin 500mg BD"})
    assert response.status_code == 200
    unresolved = next(item for item in response.json()["unresolved_items"] if item["item"] == "Crocin")
    assert '"dose_value":500.0' in unresolved["reason"]


def test_text_api_suggested_match_never_becomes_finding():
    response = client.post("/analyze-text", json={"patient": {}, "prescription_text": "Warfrin 5mg BD"})
    assert response.status_code == 200
    assert response.json()["findings"] == []
    assert response.json()["suggested_matches"][0]["suggestion"] == "Warfarin"


def test_dose_value_means_product_strength_not_per_intake_dose():
    order = parse_prescription("Tab Paracetamol 500 mg 2 tabs BD").orders[0]
    assert order.dose_value == 500
    assert order.dose_unit == "mg"
    assert order.units_per_intake == 2
    assert order.frequency_per_day == 2
    assert all(value not in {1000, 2000} for value in order.model_dump().values()
               if isinstance(value, (int, float)) and not isinstance(value, bool))
    assert "PRODUCT STRENGTH as written, not dose per intake" in (MedOrder.__doc__ or "")


def test_combination_brand_keeps_product_strength_text_without_per_ingredient_amount():
    order = parse_prescription("Tab Augmentin 625 mg BD x5 days").orders[0]
    payload = str(order.model_dump())
    assert "625 mg" in order.source_line
    assert "625 mg" in order.name_used
    assert order.dose_value is None
    assert "62.5" not in payload and "500" not in payload and "125" not in payload


@pytest.mark.parametrize("text", ["", "   ", "\x00", "😀😃😄", "😀" * 250 + "\n" + "😃" * 250])
def test_adversarial_unicode_and_empty_text_never_raise(text):
    result = parse_prescription(text)
    assert result is not None


@pytest.mark.parametrize("text", ["1 " * 150, "1-" * 150])
def test_redos_adversarial_300_char_lines_finish_under_200ms(text):
    assert len(text) == 300
    started = perf_counter()
    result = parse_prescription(text)
    elapsed = perf_counter() - started
    assert result is not None
    assert elapsed < 0.2
