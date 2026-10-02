# B19 Run A — Phase 0 baseline

Date: 2026-10-02. Tests ran with bytecode writing disabled and the project dotenv loader disabled.

## Baseline checks

- Pytest: 301 passed, 1 skipped.
- Hash inventory: 86 files under medsafe/, models/, data/ and scripts/; caches and bytecode excluded. Inventory: reports/b19_hash_before.json.
- DDI: PARTIAL, 313 rules loaded; 174 have UNSPECIFIED severity.
- DUPLICATE: RAN, 2 rules loaded.
- ALLERGY: PARTIAL, 5 reviewed rows.
- DRUG_DISEASE: PARTIAL, 5 reviewed rows.
- DOSE: NOT_RUN_NO_DATA, 0 reviewed rows.
- API synthetic request: HTTP 200. The saved pre-UI response is in reports/b19_ui_evidence.json.

## Routes and schema at baseline

Routes: GET /health, POST /analyze, POST /analyze-text.

- TextRequest: patient, prescription_text.
- Prescription: patient, new_orders.
- Patient: age, weight_kg, egfr, allergies, diagnoses, current_meds.
- MedOrder: drug_name, dose_value, dose_unit, unit_kind, frequency_per_day, route, duration_days, form, units_per_intake, frequency_code, as_needed, one_time, route_is_assumed, parse_confidence, parse_notes, unparsed_tokens, source_line, name_used, llm_assisted.
- SafetyReport: findings, unresolved_items, suggested_matches, checker_status, overall_statement, disclaimer, generated_at, kb_fingerprint, ml_status, llm_status.

The route and field inventory above records the state before the UI and age_years addition.
