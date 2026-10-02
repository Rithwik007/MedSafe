# B16 capability evidence

All inputs are synthetic. Commands below ran locally with `python -B`; API calls used FastAPI `TestClient` and made no network requests. The local checksum-verified model ran where noted. LLM provider calls stayed off; capability 9 used a fake client only.

Checker status line from outputs: `Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA.` Current checker states were DDI `PARTIAL`, duplicate `RAN`, allergy `PARTIAL`, drug-disease `PARTIAL`, and dose `NOT_RUN_NO_DATA`.

| Capability | Command and synthetic input | Key output | Product status | Covering tests |
|---|---|---|---|---|
| Free-text prescription parsing | `parse_prescription(text)` with `Combiflam BD`; `Dolo 650 TDS`; `Crocin Advance 500 OD`; `Brufen 200 SOS`; `Amoxicillin 1-0-1`. | Parsed frequency results: `Combiflam BD 2.0`; `Dolo 650 TDS 3.0`; `Crocin Advance 500 OD 1.0`; `Brufen 200 SOS` (`as_needed=True`); `Amoxicillin 1-0-1` (`2.0`). No unparsed lines. | All five orders parsed; `analyze-text` checker statuses remain `1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA`. | `test_verified_brand_maps_to_documented_ingredients`; `test_frequency_codes_load_from_csv`; `test_slot_pattern_and_matching_frequency_code_agree_by_daily_count`; `test_candidate_keeps_multiple_words`; `test_combination_brand_keeps_product_strength_text_without_per_ingredient_amount`. |
| DDI findings | `POST /analyze-text`, `patient={}`, `prescription_text="Combiflam\nDolo 650\nWarfarin"`. | HTTP 200. Findings include `DDI MAJOR` Combiflam + Warfarin, `DDI MODERATE` involving all three, and `DDI UNSPECIFIED` Combiflam + Dolo 650. | `ML ENABLED`; checker status line `1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA`. | `test_api_health_and_report`; `test_ddinter_evidence_keeps_source_and_pair_ids`; `test_unspecified_ddinter_rule_emits_review_warning_below_moderate`. |
| Duplicate medication | Same synthetic request as DDI case. | `DUPLICATE MODERATE` Combiflam + Dolo 650; shared ingredient is paracetamol. | Duplicate `RAN` (2 policy rows). | `test_combiflam_and_dolo_650_report_paracetamol_duplicate`; `test_duplicate_recommendation_rationale_and_orders_label`. |
| Allergy conflict | `POST /analyze-text`, allergy `amoxicillin`, order `Amoxicillin`. | `ALLERGY UNSPECIFIED`, rule `B14-ALG-001`; exact allergy ingredient match. | Allergy `PARTIAL` (5 rows); overall `1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA`. | `test_allergy_direct_match_uses_promoted_row_text_and_unknown_severity`. |
| Drug-disease finding and unresolved condition | `POST /analyze-text`, diagnoses `myasthenia gravis`, `adrenal insufficiency`; orders `Amoxicillin`, `Ciprofloxacin`. | `DRUG_DISEASE UNSPECIFIED`, rule `B14-DIS-004`, for ciprofloxacin + myasthenia gravis. `adrenal insufficiency` appears in unresolved items because the reviewed label row is for `uncorrected adrenal insufficiency`, and matching uses exact phrases. | Drug-disease `PARTIAL` (5 rows); unresolved condition retained. | `test_drug_disease_exact_match_uses_promoted_row_text`; `test_nonmatching_allergen_and_condition_are_unresolved_not_findings`. |
| Dose-limit checks | Same analyze result; inspected `checker_status` and `data/seed/dose_limits.csv`. | Dose status has 0 rules. No dose finding is produced. | `NOT_RUN_NO_DATA`. | `test_missing_patient_inputs_are_explicit_in_partial_status`; `test_checker_status_has_clinical_checkers_partial_and_dose_no_data`. |
| Explainable report and REST API | `TestClient(app).post('/analyze', json={'patient': {'current_meds':[{'drug_name':'Warfarin'}]}, 'new_orders':[{'drug_name':'Ibuprofen'}]})`. | HTTP 200; JSON includes rule findings, severity, source evidence, explanations, checker statuses, and unresolved items. The report includes the rule-based Warfarin + ibuprofen finding. | API returned HTTP 200; checker status line `1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA`. | `test_api_health_and_report`; `test_rendered_checker_output_has_no_rule_7_banned_phrases`; `test_demo_snapshot_combiflam_dolo_warfarin`. |
| ML note and withheld estimate | Local model input `Lisinopril` + `Levothyroxine` produced an ML note on an `UNSPECIFIED` DDI pair (`Minor`, `ML-PREDICTED, unverified`). Separately, the real engine received an injected synthetic predictor returning `Major` for that same unspecified pair; the Major gate withheld its estimate. The API wording renderer turns the internal gate count into `1 estimate withheld pending outside review`; rendered user text contains no predicted class. A 30-drug synthetic batch reproduced `9 MAJOR_WITHHELD`, `62 BELOW_THRESHOLD`, and `139 PAIR_ALREADY_LABELED`. | Local model `ENABLED`; individual fake Major estimate withheld; no ML note attached to that finding. All-whitelist run attached 103 notes and counted 9 withheld. | `ENABLED`; withheld wording `estimate withheld pending outside review`. | `test_ml_note_only_attaches_to_unspecified_ddi_and_preserves_findings`; `test_major_ml_estimate_withheld_and_other_labels_unchanged`; `test_api_json_omits_withheld_major_class`; `test_same_input_and_fake_predictor_render_deterministically`. |
| Optional LLM layer, fake client only | `fallback_parse` on `Paracetamol 500 mg tablet, take one twice daily for 3 days`; local `Fake` returns a guarded JSON extraction. No provider client or API key used. | `parse_attempted=1`, `parse_accepted=1`, `parse_rejected=0`; parsed frequency `BD`; `llm_assisted=True`. | Fake fallback accepted one extraction; live provider remained OFF/not called. | `test_valid_fallback_is_guarded_and_capped`; `test_guarded_summary_renders_with_label_and_only_structured_fields`; `test_disabled_by_default_and_missing_key`. |

## Exact command forms

The evidence harness ran in PowerShell as `@' ... '@ | python -B -`, using these calls:

```python
parse_prescription(text)
TestClient(app).post("/analyze-text", json={"patient": {...}, "prescription_text": "..."})
TestClient(app).post("/analyze", json={"patient": {...}, "new_orders": [...]})
analyze(Prescription(...), ml_predictor=injected_predictor)
fallback_parse(line, parsed, fake_config, Fake([guarded_json]), True)
```

No real-LLM test ran. No API key was read or written. No network access was used.
