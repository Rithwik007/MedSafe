## Demo 1 — first 40 lines (reports/b161_demo_1.txt)

```text
MedSafe medication safety report
Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA. Findings by severity: MAJOR 1, MODERATE 2, UNSPECIFIED 1. Absence of findings does not mean the prescription is safe.
1 finding(s) carry an unverified ML estimate; these are not database classifications.
ML estimates come from a model trained on DDInter labels. They are not DDInter database classifications and have not been validated against outside sources at scale. A pharmacist must review each estimate.
Generated at: 2026-10-02T08:28:28.999213+00:00
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

## Demo 2 — first 40 lines (reports/b161_demo_2.txt)

```text
MedSafe medication safety report
Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA. Findings by severity: UNSPECIFIED 3. Absence of findings does not mean the prescription is safe.
Generated at: 2026-10-02T08:28:31.358918+00:00
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

## Demo 3 — first 40 lines (reports/b161_demo_3.txt)

```text
MedSafe medication safety report
Checkers: 1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA. Findings by severity: UNSPECIFIED 1. Absence of findings does not mean the prescription is safe.
1 finding(s) carry an unverified ML estimate; these are not database classifications.
ML estimates come from a model trained on DDInter labels. They are not DDInter database classifications and have not been validated against outside sources at scale. A pharmacist must review each estimate.
Generated at: 2026-10-02T08:28:33.328910+00:00
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
