# B16 final report

## Result

B16 evidence and the synthetic demo are complete. The source code, model artifacts, and data were not intentionally edited. Two hard requirements remain unsatisfied: the full SHA inventory changed in generated Python bytecode caches, and the existing README/.gitignore could not be edited under the prompt’s instruction to leave existing files untouched.

## 1. Integrity and tests

All full-suite runs reported 301 passed, 1 skipped. The skipped case is the opt-in live LLM test. B16 made no training, threshold selection, or held-out-label evaluation; `TEST_SPLIT_TOUCH=0` for this task. Local inference only.

| Checkpoint | Result |
|---|---|
| Before Part A | 301 passed, 1 skipped; 57.48s |
| After Part A | 301 passed, 1 skipped; 53.28s |
| Before Part B | 301 passed, 1 skipped; 53.48s |
| After Part B / before demo execution | 301 passed, 1 skipped; 112.18s |
| After Part C | 301 passed, 1 skipped; 75.08s |
| After Part D / before Part E | 301 passed, 1 skipped; 64.58s |
| After Part E | 301 passed, 1 skipped; 70.25s |
| Focused REST API check | 1 passed; 7.58s |

SHA-256 inventory covers `medsafe/`, `models/`, and `data/`. Before: 106 files. After: 108 files. The full diff is **not empty**: two generated `.pyc` files were added and three existing `.pyc` files were recompiled. The test `test_api_analyze_survives_missing_optional_ml_package_in_subprocess` starts Python without `-B`; it caused the cache writes despite the outer `python -B -m pytest` command. No `.py` source, model, or data file changed. The cache changes are ignored by the project `.gitignore`, but B16’s literal empty-diff condition failed.

Diff file: `reports/b16_hash_diff.txt`. Before and after inventories: `reports/b16_hash_before.json` and `reports/b16_hash_after.json`.

```json
[
  {
    "path": "medsafe/checkers/__pycache__/allergy.cpython-311.pyc",
    "before": null,
    "after": "7b13d07566ed7dc2dcd5986d835da855371129ae2ae06903ff145e61ec2570e8"
  },
  {
    "path": "medsafe/checkers/__pycache__/drug_disease.cpython-311.pyc",
    "before": null,
    "after": "d19b38639b933373c355f53e76a878d97062f9ab40a4ff27053662d902ecf25f"
  },
  {
    "path": "medsafe/checkers/__pycache__/engine.cpython-311.pyc",
    "before": "65a01796534e07c9087dc4fb5c4f882d1cd8311dcbc96bb604a159317972a2c6",
    "after": "b8b8515db3db0ad695f217ccf764f29ec354274c3050380ec7ea436856e8cce6"
  },
  {
    "path": "medsafe/checkers/__pycache__/stubs.cpython-311.pyc",
    "before": "a39cd60d217337ab5f5e862513ae50506a26ca4549309f1a945115d7f64f1f95",
    "after": "2a90ccdfa22f1af76dd8f554826e5fc66d63fece07f3f74332341ed4b0f31bc2"
  },
  {
    "path": "medsafe/explain/__pycache__/templates.cpython-311.pyc",
    "before": "6b06738213b1336aeafb8b6df263aa06fff8914866078d4b14687e4da75dc254",
    "after": "d24b629ad359d6b025eede39970046a957892dd651f59ffda32386e8f815ee82"
  }
]
```

## 2. Part A: deck facts

# B16 deck facts

Counts below come from local project files. A count is not a clinical validation result.

| Fact | Value | Source and count method | OK to show on a slide? |
|---|---:|---|---|
| DDI rules loaded | 313 | `data/seed/rules.csv`; count data rows loaded by `medsafe/kb/rules.py`. | Yes |
| Distinct drugs covered by DDI rules | 30 | `data/seed/rules.csv`; split each DDI `drugs` field and count distinct names. | Yes |
| DDI rules with `UNSPECIFIED` severity | 174 | `data/seed/rules.csv`; count DDI rows with severity `UNSPECIFIED`. | Yes |
| Duplicate-policy rows | 2 | `data/seed/duplicate_policy.csv`; count data rows. | Yes |
| Allergy rows | 5 | `data/seed/allergy_rules.csv`; count reviewed data rows loaded. | Yes |
| Drug-disease rows | 5 | `data/seed/drug_disease_rules.csv`; count reviewed data rows loaded. | Yes |
| Dose rows | 0 | `data/seed/dose_limits.csv`; header-only, zero data rows. | Yes |
| Demo drug whitelist | 30 | `data/seed/drug_whitelist.csv`; one header plus 30 entries (the header is the first drug name). | Yes |
| Verified brand-to-ingredient mappings | 13 | `data/seed/synonyms.csv`; count rows with `verified=yes` and nonempty `ingredients`; 16 rows total, 3 unresolved brand-family rows. | Yes |
| DDInter total unique pairs | 160,235 | `reports/ml_data_audit.md`; local DDInter audit, canonicalized pairs, highest severity retained. | Yes |
| DDInter unique drugs | 1,939 | `reports/ml_data_audit.md`; unique canonical drug names. | Yes |
| DDInter Unknown-severity pairs | 29,813 | `reports/ml_data_audit.md`; deduplicated unique pairs labeled Unknown. | Yes |
| Tests | 301 passed, 1 skipped | `python -B -m pytest -q`; B16 baseline and Part A post-run. | Yes |
| ML Unknown-severity pairs | 29,813 | `reports/ml_unknown_distribution.md`; overall DDInter Unknown-pair denominator. | Yes |
| Major estimates withheld on UNSPECIFIED rules | 9 | `reports/b13_exposure.md`; re-scored 174 unspecified rules with frozen model/tau. | Yes |
| B12 spot-check tally rows | 29 recorded | `reports/b13_decision_outcome.md`; tally categories sum to 29. The underlying `reports/b12_pass1_blind.csv` has only 25 rows, so this count is inconsistent and must be reconciled. | Yes, only with discrepancy stated |
| B12 definite agree | 1 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |
| B12 definite disagree | 1 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |
| B12 unclear | 23 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |
| B12 not retrievable | 4 | `reports/b13_decision_outcome.md`; recorded tally. | Yes, only with discrepancy stated |

## Limits for slides

The B12 tally has a source-row mismatch: its recorded categories total 29, while the blind CSV contains 25 rows. Treat its counts as unreconciled. The report also says 0 of 9 Major model outputs had a definite outside-source answer. Major ML notes remain suppressed. The spot check is small and does not establish model performance.

Do not claim the prototype checks all 160,235 DDInter pairs. It loads 313 DDI rules for the 30-drug whitelist, and the model can make unverified estimates beyond those rules.

## 3. Part B: capability evidence

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

## 4. Part C: demos and API commands

Each demo ran three times through the in-process API with ML enabled and `use_llm=false`. Comparisons passed after removing only `generated_at` from JSON and replacing only the generated-at line in text. Full outputs are in `reports/demo/demo_1.txt` through `demo_3.txt` and matching JSON files. The full run log is `reports/b16_demo_run.txt`.

### Demo 1: first 40 lines

```text
MedSafe medication safety report
Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA. Findings by severity: MAJOR 1, MODERATE 2, UNSPECIFIED 1. Absence of findings does not mean the prescription is safe.
1 finding(s) carry an unverified ML estimate; these are not database classifications.
ML estimates come from a model trained on DDInter labels. They are not DDInter database classifications and have not been validated against outside sources at scale. A pharmacist must review each estimate.
Generated at: 2026-10-02T07:57:28.511034+00:00
Knowledge base SHA-256: 94197414b08525085da9fa15f829a9adf199cac12316d0f3bfadfbbb97add6dc

Checker status:
- DDI: PARTIAL (313 rules; 174/313 loaded DDI rules have UNSPECIFIED severity (>25%). No class-level DDI rules loaded.)
- DUPLICATE: RAN (2 rules; Duplicate policy loaded.)
- ALLERGY: PARTIAL (5 rules; 5 reviewed rows loaded. Coverage is a handful of source-text-checked label rows; this is not clinical review. No patient allergy data supplied; no exact allergy match was evaluated.)
- DRUG_DISEASE: PARTIAL (5 rules; 5 reviewed rows loaded. Coverage is a handful of source-text-checked label rows; condition matching uses exact phrases only and this is not clinical review. No patient condition data supplied; no exact drug-condition match was evaluated.)
- DOSE: NOT_RUN_NO_DATA (0 rules; No reviewed rows in dose_limits.csv; checker not run.)
- ML estimate: ENABLED (Local checksum-verified model loaded; estimates remain unverified. 2 pairs already have source classifications)
- LLM: DISABLED (Per-request use_llm flag is off.)

Findings:
- MAJOR: warfarin + ibuprofen
  Risk: DDInter lists this pair at Major severity.
  Why: Mechanism not provided by the source dataset.
  Trigger: Ingredients: warfarin + ibuprofen. Orders: Combiflam, Warfarin.
  Recommendation: No management guidance in the source dataset. Ask a pharmacist or check an authoritative label.
  Source: https://ddinter.scbdd.com/download/ (DDInter IDs: DDInter1951, DDInter900)
  Review: Not reviewed
- MODERATE: paracetamol + warfarin
  Risk: DDInter lists this pair at Moderate severity.
  Why: Mechanism not provided by the source dataset.
  Trigger: Ingredients: paracetamol + warfarin. Orders: Combiflam, Dolo 650, Warfarin.
  Recommendation: No management guidance in the source dataset. Ask a pharmacist or check an authoritative label.
  Source: https://ddinter.scbdd.com/download/ (DDInter IDs: DDInter14, DDInter1951)
  Review: Not reviewed
- MODERATE: Duplicate paracetamol
  Risk: Duplicate policy flags this at Moderate severity.
  Why: Not applicable to duplicate-therapy findings.
  Trigger: Shared ingredient: paracetamol. Orders: Combiflam, Dolo 650.
  Recommendation: Confirm both orders are intended. Ask the prescriber or pharmacist to check the combined daily amount of the shared ingredient.
  Source: duplicate_policy.csv
  Review: Not reviewed
- UNSPECIFIED: paracetamol + ibuprofen
  Risk: DDInter lists this pair at Unspecified severity.
```

### Demo 2: first 40 lines

```text
MedSafe medication safety report
Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA. Findings by severity: UNSPECIFIED 3. Absence of findings does not mean the prescription is safe.
Generated at: 2026-10-02T07:57:32.003115+00:00
Knowledge base SHA-256: 94197414b08525085da9fa15f829a9adf199cac12316d0f3bfadfbbb97add6dc

Checker status:
- DDI: PARTIAL (313 rules; 174/313 loaded DDI rules have UNSPECIFIED severity (>25%). No class-level DDI rules loaded.)
- DUPLICATE: RAN (2 rules; Duplicate policy loaded.)
- ALLERGY: PARTIAL (5 rules; 5 reviewed rows loaded. Coverage is a handful of source-text-checked label rows; this is not clinical review.)
- DRUG_DISEASE: PARTIAL (5 rules; 5 reviewed rows loaded. Coverage is a handful of source-text-checked label rows; condition matching uses exact phrases only and this is not clinical review.)
- DOSE: NOT_RUN_NO_DATA (0 rules; No reviewed rows in dose_limits.csv; checker not run.)
- ML estimate: ENABLED (Local checksum-verified model loaded; estimates remain unverified. 1 pair below model threshold)
- LLM: DISABLED (Per-request use_llm flag is off.)

Findings:
- UNSPECIFIED: ciprofloxacin + amoxicillin
  Risk: DDInter lists this pair at Unspecified severity.
  Why: Mechanism not provided by the source dataset.
  Trigger: Ingredients: ciprofloxacin + amoxicillin. Orders: Amoxicillin, Ciprofloxacin.
  Recommendation: No management guidance in the source dataset. Ask a pharmacist or check an authoritative label. Severity was not classified by the source.
  Source: https://ddinter.scbdd.com/download/ (DDInter IDs: DDInter384, DDInter83)
  Review: Not reviewed
- UNSPECIFIED: Amoxicillin
  Risk: Allergy finding has Unspecified severity.
  Why: Mechanism not provided by the source dataset.
  Trigger: Label category: CONTRAINDICATION. Label contraindicates amoxicillin in patients with a history of serious hypersensitivity to amoxicillin.
  Recommendation: Label contraindication applies to the stated serious hypersensitivity history. Ask a pharmacist to review this label-based finding. Severity was not classified by the source.
  Source: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=641ec2a8-368a-4c5c-8c11-37366a06ce93
  Review: Source text verified; not clinical review
- UNSPECIFIED: Ciprofloxacin
  Risk: Drug Disease finding has Unspecified severity.
  Why: Mechanism not provided by the source dataset.
  Trigger: Label category: WARNING. Label states ciprofloxacin may exacerbate muscle weakness in myasthenia gravis and says to avoid it in patients with a known history.
  Recommendation: Label says to avoid ciprofloxacin in patients with a known history of myasthenia gravis. Ask a pharmacist to review this label-based finding. Severity was not classified by the source.
  Source: https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b283d662-9be1-49c7-be03-cb21055314c1
  Review: Source text verified; not clinical review

Unresolved items:
- adrenal insufficiency: No exact reviewed drug-condition rule matched this condition; this does not establish absence of a concern.
- Amoxicillin: Parser note: frequency not stated or unresolved
```

### Demo 3: first 40 lines

```text
MedSafe medication safety report
Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA. Findings by severity: UNSPECIFIED 1. Absence of findings does not mean the prescription is safe.
1 finding(s) carry an unverified ML estimate; these are not database classifications.
ML estimates come from a model trained on DDInter labels. They are not DDInter database classifications and have not been validated against outside sources at scale. A pharmacist must review each estimate.
Generated at: 2026-10-02T07:57:35.469226+00:00
Knowledge base SHA-256: 94197414b08525085da9fa15f829a9adf199cac12316d0f3bfadfbbb97add6dc

Checker status:
- DDI: PARTIAL (313 rules; 174/313 loaded DDI rules have UNSPECIFIED severity (>25%). No class-level DDI rules loaded.)
- DUPLICATE: RAN (2 rules; Duplicate policy loaded.)
- ALLERGY: PARTIAL (5 rules; 5 reviewed rows loaded. Coverage is a handful of source-text-checked label rows; this is not clinical review. No patient allergy data supplied; no exact allergy match was evaluated.)
- DRUG_DISEASE: PARTIAL (5 rules; 5 reviewed rows loaded. Coverage is a handful of source-text-checked label rows; condition matching uses exact phrases only and this is not clinical review. No patient condition data supplied; no exact drug-condition match was evaluated.)
- DOSE: NOT_RUN_NO_DATA (0 rules; No reviewed rows in dose_limits.csv; checker not run.)
- ML estimate: ENABLED (Local checksum-verified model loaded; estimates remain unverified.)
- LLM: DISABLED (Per-request use_llm flag is off.)

Findings:
- UNSPECIFIED: levothyroxine + lisinopril
  Risk: DDInter lists this pair at Unspecified severity.
  Why: Mechanism not provided by the source dataset.
  Trigger: Ingredients: levothyroxine + lisinopril. Orders: Lisinopril, Levothyroxine.
  Recommendation: No management guidance in the source dataset. Ask a pharmacist or check an authoritative label. Severity was not classified by the source.
  Source: https://ddinter.scbdd.com/download/ (DDInter IDs: DDInter1064, DDInter1079)
  Review: Not reviewed
  ML-PREDICTED (unverified): Experimental ML estimate (unverified, not a database classification): possibly Minor. Estimated from patterns in other DDInter-classified pairs; other sources may disagree. Pharmacist review is still required. This estimate does not lower the need for review.

Unresolved items:
- mystery: Drug name did not resolve exactly; parsed fields retained: {"drug_name":"mystery","dose_value":null,"dose_unit":null,"unit_kind":null,"frequency_per_day":null,"route":null,"duration_days":null,"form":null,"units_per_intake":null,"frequency_code":null,"as_needed":false,"one_time":false,"route_is_assumed":false,"parse_confidence":"LOW","parse_notes":["Slot pattern '7-3-1' has unequal non-zero quantities; frequency unresolved.","frequency not stated or unresolved","quantity per intake not stated","Drug name did not resolve exactly; no medication checks applied."],"unparsed_tokens":["syrup","xyz"],"source_line":"mystery syrup xyz 7-3-1","name_used":"mystery","llm_assisted":false}
- mystery syrup xyz 7-3-1: Unparsed token: syrup
- mystery syrup xyz 7-3-1: Unparsed token: xyz
- mystery syrup xyz 7-3-1: Parser note: Slot pattern '7-3-1' has unequal non-zero quantities; frequency unresolved.
- mystery syrup xyz 7-3-1: Parser note: frequency not stated or unresolved
- mystery syrup xyz 7-3-1: Parser note: quantity per intake not stated
- Lisinopril: Parser note: frequency not stated or unresolved
- Lisinopril: Parser note: quantity per intake not stated
- Levothyroxine: Parser note: frequency not stated or unresolved
- Levothyroxine: Parser note: quantity per intake not stated

Suggested matches:
- None.
```

API server command:

```powershell
python -m uvicorn medsafe.api.app:app --reload
```

curl sample:

```bash
curl -X POST "http://127.0.0.1:8000/analyze-text?use_llm=false" \
  -H "Content-Type: application/json" \
  -d '{"patient":{"allergies":["amoxicillin"],"diagnoses":["myasthenia gravis"]},"prescription_text":"Amoxicillin\nCiprofloxacin"}'
```

PowerShell sample:

```powershell
$body = @{ patient = @{ allergies = @("amoxicillin"); diagnoses = @("myasthenia gravis") }; prescription_text = "Amoxicillin`nCiprofloxacin" } | ConvertTo-Json -Depth 8
Invoke-RestMethod -Uri "http://127.0.0.1:8000/analyze-text?use_llm=false" -Method Post -ContentType "application/json" -Body $body
```

### REST probe note

One ad hoc `TestClient` call to structured `POST /analyze` did not return during a 60-second wait and was interrupted. The full suite passed, and the focused existing REST test passed (`1 passed` in 7.58s). The three B16 demo requests used `POST /analyze-text` and completed. This stall was not reproduced in the focused test; no product code was changed.

## 5. Part D: README, ignore rules, and sizes

The root `README.md` and `.gitignore` already existed. B16 says to leave existing files untouched, so neither was edited. Proposed README replacement is in `reports/b16_readme_draft.md`; ignore suggestions are in `reports/b16_gitignore_recommendation.md`.

README draft covers: project purpose; installation; tests; demo; API with curl and PowerShell; DDInter and DailyMed sources; architecture; limitations; and the exact notice “Research prototype, not for clinical use.” It contains no performance metrics.

On-disk sizes: `models/` 7,515,007 bytes (7.17 MiB); `data/` 13,259,656 bytes (12.65 MiB); raw DDInter directory 13,135,540 bytes (12.53 MiB). Recommend excluding the eight raw DDInter CSV downloads until the owner confirms that redistribution terms permit it. Keep attribution/source notes if distributing data under permitted terms. Models total 7.17 MiB and are required for the local ML demo.

## 6. Part E: hygiene scan

Full scan: `reports/b16_hygiene_scan.md`. No API-key pattern or email found. No verified phone number found; two number-pattern matches were DDInter identifiers inside source URLs. Findings:

- `README.md:14`: absolute checkout path and account name.
- `reports/b14_final_report.md:7`: reviewer name.
- `reports/b14_staging/allergy_rules.csv:2-6`: reviewer field.
- `reports/b14_staging/drug_disease_rules.csv:2-6`: reviewer field.
- `reports/b14_staging/review_note.txt:1`: reviewer name.

The hygiene scan is not clean. Do not publish affected files until the owner chooses how to handle the local path and reviewer identifiers.

## 7. Problems and surprising behavior

- B12 decision outcome records 29 tally rows: 1 agree, 1 disagree, 23 unclear, 4 not retrievable. `reports/b12_pass1_blind.csv` contains 25 rows. The tally remains unreconciled. The recorded B13 result says 0 of 9 Major predictions had definite answers, so Major ML notes stay suppressed.
- Demo 2 correctly surfaces `adrenal insufficiency` as unresolved because the sourced row is for `uncorrected adrenal insufficiency` and matching is exact-phrase only.
- First direct run of the new demo script failed to import `medsafe` because Python did not place the project root on `sys.path`. The new script was adjusted to add its own project root; the next runs passed. No existing product code changed.
- A single manual structured API probe stalled once; the existing focused REST test passed, as noted above.

## 8. Not done

- No live LLM/provider test, API-key use, network call, model retraining, threshold change, push, or feature change.
- Existing README and `.gitignore` remain unchanged per the B16 no-edit rule. Their proposed updates are drafts only.
- The full hash diff is not empty because the required tests spawned Python without bytecode suppression and changed local caches. No source, data, or model artifact changed.
