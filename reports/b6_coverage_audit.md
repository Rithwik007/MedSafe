# B6 parser coverage audit

`tests/test_parser_rx.py` has 114 collected cases. Counts below track cases by parser dimension, so categories can overlap. This is parser coverage, not clinical-rule coverage.

| Category | Cases | Example test name |
|---|---:|---|
| Form tokens | 16 | `test_dosage_form_tokens_load_from_csv` |
| Frequency codes (all CSV rows) | 14 | `test_frequency_codes_load_from_csv` |
| Conflicting/repeated frequency codes and scheduled/PRN pairs | 7 | `test_scheduled_and_as_needed_frequency_conflict` |
| Slot patterns (five required; plus fractional and conflict cases) | 9 | `test_slots_count_nonzero_times_and_quantities` |
| Durations (days, weeks, unsupported months) | 7 | `test_supported_duration_forms` |
| Routes | 6 | `test_explicit_routes_override_form_assumption` |
| Bare number handling | 2 | `test_bare_number_is_not_assumed_to_be_mg` |
| Brand-with-number resolution | 3 | `test_brand_with_strength_number_is_exactly_resolved_but_not_strength` |
| Unresolved brand cases | 3 | `test_crocin_500mg_stays_unresolved_and_keeps_strength` |
| Unparsed lines | 2 | `test_no_name_candidate_becomes_unparsed_line` |
| Leftover tokens | 4 | `test_leftover_tokens_are_not_dropped` |
| Line splitting (newline, semicolon, comma rule) | 3 | `test_newline_and_semicolon_split_lines` |
| List-marker stripping | 4 | `test_all_list_marker_forms_are_stripped` |
| Input limits (total, lines, per-line, plus HTTP 422) | 4 | `test_parser_input_limits_raise_clear_error` |
| Old narrow format compatibility | 1 | `test_legacy_unpacking_returns_old_pair_shape` |
| Units and unit kinds (mass, volume, IU) | 9 | `test_units_load_from_csv_without_value_conversion` |
| Garbage and adversarial text never raises | 7 | `test_adversarial_unicode_and_empty_text_never_raise` |

Mismatch recorded: `take the blue one daily` becomes an unresolved candidate order, not `unparsed_lines`. No parser matching change made, as requested.

Every listed parser dimension has at least one collected case. Clinical allergy, drug-disease, and dose checker rows remain empty; this table does not claim clinical-rule coverage.
