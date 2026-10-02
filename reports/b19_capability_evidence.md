# B19 capability evidence

All inputs below are synthetic. Tests ran with dotenv loading disabled. Live LLM use is summarized in its separate measurement report.

| Capability | Command/input | Observed output | Covering tests | Product status |
|---|---|---|---|---|
| Free-text parsing | python -B scripts/run_demo.py; Demo 1 input: Combiflam, Dolo 650, Warfarin. Demo 3 includes “mystery syrup xyz 7-3-1”. | Demo 1 resolves the known names; Demo 3 preserves the unresolved text. Three demo outputs repeat identically except generated_at. | tests/test_parser_rx.py, tests/test_b19_ui.py | PARTIAL |
| DDI | Demo 1: Combiflam, Dolo 650, Warfarin. | Rule-based Major finding DDINTER-DDInter1951-DDInter900 remains. DDI: PARTIAL (313 rules; 174 UNSPECIFIED). | tests/test_ddi_combo.py, tests/test_report.py | PARTIAL |
| Duplicate therapy | Demo 1: Combiflam and Dolo 650. | DUPLICATE-POLICY-INGREDIENT appears; DUPLICATE: RAN (2 rules). | tests/test_duplicate.py | BUILT |
| Allergy | Demo 2: Amoxicillin with allergy amoxicillin. | B14-ALG-001 appears as UNSPECIFIED from a source-text-checked label row. ALLERGY: PARTIAL (5 rules). | tests/test_clinical_checkers.py, tests/test_b19_ui.py | PARTIAL |
| Drug-disease | Demo 2: Ciprofloxacin with diagnosis myasthenia gravis. | B14-DIS-004 appears as UNSPECIFIED from a source-text-checked label row. DRUG_DISEASE: PARTIAL (5 rules; exact phrase matching). | tests/test_clinical_checkers.py, tests/test_b19_ui.py | PARTIAL |
| Dose | Demo supplement: age_years 35; atorvastatin 40 mg, 2 tabs, TDS, oral. | DOSE: PARTIAL (1 rule). The finding reports this order's arithmetic against the recorded label row. Second input with age omitted surfaces “dose not checked: patient age not provided”. | tests/test_dose_checker.py, tests/test_validate_checker_csvs.py | PARTIAL |
| ML estimate | Demo 3: Lisinopril and Levothyroxine with ML on and LLM off. | An UNSPECIFIED DDI finding carries “ML-PREDICTED (unverified)” estimate text. Rule severity stays UNSPECIFIED. | tests/test_ml_reporting.py, tests/test_ml_pipeline.py | PARTIAL |
| Major estimate withholding | Frozen B13 exposure over 174 UNSPECIFIED rules; current policy remains enabled. | 9 estimates withheld pending outside review; the withheld class is not exposed in user-facing status. | tests/test_ml_reporting.py, reports/b13_decision_outcome.md | BUILT |
| Explainable report and REST API | FastAPI TestClient and local server; POST /analyze-text using the three demo inputs. | HTTP 200; finding order and report fields come from the API. GET /health and /config returned HTTP 200. | tests/test_report.py, tests/test_b19_ui.py | BUILT |
| Web UI | GET /, /static/app.js, /static/styles.css, /config; then load each synthetic demo. | Each route returned HTTP 200 with CSP. UI renders API findings in returned order. No screenshots were taken. | tests/test_b19_ui.py | BUILT |
| LLM provider | Live Groq measurement: 25 parser lines plus 15 real-pipeline summary cases. | 0/25 parser cases and 0/15 summaries accepted; findings unchanged in 40/40 cases. Offline provider and guard behavior uses simulated clients. | tests/test_llm_layer.py, tests/test_b19_llm_config.py, reports/b19_llm_measurement.json | PARTIAL |

Supplementary dose reports: reports/demo/dose_over_limit.txt and reports/demo/dose_missing_age.txt.
