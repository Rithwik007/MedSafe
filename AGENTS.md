PROJECT: MedSafe, medication-safety decision-support demo. Not for clinical use.

RULES (numbered):
1. Never invent medical facts: no interactions, severities, mechanisms, doses, ATC codes, brand-to-ingredient mappings, or cross-reactivity. Clinical knowledge lives only in CSV files under data/, each row with source URL, source section, and access date.
2. Never put clinical sentences in Python code. Fixed fallback strings are allowed only if listed in medsafe/explain/templates.py.
3. No LLM or network call inside checkers, parser, normalizer, explainer templates, or the ML predictor. LLM calls are allowed only inside medsafe/llm/, invoked from the API layer. LLM output never creates, removes, re-ranks or changes the severity of a finding.
4. Additive schema changes only. Never rename, remove or retype Finding, Evidence, MedOrder fields. If a field is missing, stop and ask with the exact field name.
5. Never weaken an old test. List every changed assertion with a reason.
6. A checker with no reviewed rows must report NOT_RUN_NO_DATA. Never return an empty "all clear".
7. Never use the words "safe to use", "no risk", "approved" in output.
8. Unresolved input is surfaced, never dropped or guessed.
9. Run `python -m pytest -q` before and after every change; report counts.
10. Print requested evidence in full. If it is long, save it under reports/ and print the first 40 lines plus the file path.
11. Do not modify files outside the scope named in the task.
12. Ask before adding dependencies.
13. ML output is always labeled ML-PREDICTED and unverified. It never changes the severity, ordering or presence of a rule-based finding.
14. Never tune any threshold or gate after seeing test-split results.
15. Model artifacts load only from local models/ after SHA-256 verification.
16. LLM output is untrusted text. It is accepted only after programmatic guards pass; otherwise the deterministic output is used.
17. LLM is OFF by default. It needs an API key in the environment AND an explicit per-request flag.
18. API keys never appear in code, logs, reports, test fixtures or git. Real patient data is never sent to an LLM; demos use synthetic data only.

CURRENT STATE
Tests: 329 passed, 1 skipped (2026-10-02; opt-in live LLM test is skipped in offline runs).
Implemented modules:
- medsafe/api: FastAPI endpoints and vanilla static web interface; age_years is optional.
- medsafe/nlp: prescription parser; unresolved lines remain visible.
- medsafe/core: drug normalizer, ingredient names, report model.
- medsafe/kb: CSV rules and NetworkX graph.
- medsafe/checkers: DDI, duplicate therapy, exact-match allergy and drug-disease checks, and adult single-order dose checks over one source-text-checked DailyMed row. Dose status is PARTIAL; source-text check is not clinical review.
- medsafe/explain: deterministic explanations and unverified ML notes.
- medsafe/models: additive report and prediction models.
- medsafe/ml: offline DDInter severity data audit, leakage-safe splits, training, evaluation, and checksum-verified prediction; optional ml dependencies.
- medsafe/llm: optional Anthropic and Groq providers; off by default, terminal and per-request opt-in required, fixed guards and deterministic fallback.
- medsafe/ml: estimates remain restricted to DDInter Unknown-severity pairs; predicted Major notes remain withheld. Tau, gate, model artifacts and ML code remain frozen.
- scripts/validate_checker_csvs.py: source-schema and row checks; allergy and drug-disease files each have five source-text-checked rows; dose file has one such row.
- B12 spot check: 25 unique pairs; 1 agree, 1 disagree, 19 unclear, 4 not retrievable. Major ML notes remain suppressed under the frozen rule.
- B19 evidence: reports/b19_final_report.md; capability table: reports/b19_capability_evidence.md; deck facts: reports/b19_deck_facts.md; paste-ready deck block: reports/final_status_block.md.
- B19 live synthetic Groq measurement: 0/25 parser cases and 0/15 summary cases accepted; findings unchanged in 40/40 cases.
- Submission archive: reports/medsafe_submission.zip; excludes .env, work/, caches and raw DDInter dumps.
