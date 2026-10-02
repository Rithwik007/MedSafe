# B17a.1 and B16.2 Read-only results — 2026-10-02

## B17a.1

### Test counts and file integrity

- Original project before diagnosis: **301 passed, 1 skipped**.
- Original project after diagnosis: **301 passed, 1 skipped**.
- SHA-256 check: unchanged existing files unchanged; no existing file missing. The allowed new B17a.1 and B16.2 reports are excluded from the baseline comparison.
- `PYTHONDONTWRITEBYTECODE=1` was set. No key or LLM used. `.env` was not opened or printed.

### Part A — Existing B17a candidates

The prior B17a report records **no exact product label, setid, quoted dose statement, or fetch failure for any candidate**. These candidates were considered and skipped for the recorded reasons below; current labels fetched for Part D were not used in the earlier B17a staging decision.

| Candidate | Label / setid recorded in B17a | Dose statement recorded | Exact skip reason in B17a |
|---|---|---|---|
| Acetaminophen OTC | None | None | Directions give caplet counts per interval and per 24 hours; no direct maximum mass; conversion from strength was disallowed; no direct single-dose mass maximum. |
| Ibuprofen OTC | None | None | Tablet counts/frequency rather than maximum single/daily mass; count-to-mass conversion disallowed. |
| Metformin | None | None | Indication/titration/renal context; daily maximum did not supply matching explicit single-dose maximum. |
| Atorvastatin | None | None | Daily/context-dependent range; no explicit single-dose mass maximum; adult-only row with blank ages conflicts with validator. |
| Simvastatin | None | None | Limits vary by indication/interacting therapy; no single universal row satisfying prompt and validator. |
| Aspirin | None | None | OTC tablet counts and intervals, not direct maximum mass; conversion disallowed. |
| Lisinopril | None | None | Indication/titration-dependent; no direct maximum single-dose field satisfying schema. |
| Digoxin | None | None | Individualized by age, lean body weight, renal function and titration; no universal numeric maximum row. |

No fetch failure was documented in the existing B17a candidate report. Its reasons concern representability/constraints, not a recorded failed URL.

### Part B — Parser semantics

`dose_value` and `dose_unit` represent the product strength as written, not the dose taken each time. Dose per intake can only be derived as strength × `units_per_intake` (and not for combination products). `HIGH` confidence currently means a resolved medicine, strength or brand, frequency, no leftover tokens and no frequency conflict; it does **not** ensure the intake quantity is known.

| Synthetic input | dose_value | dose_unit | unit_kind | units_per_intake | frequency_per_day | route | as_needed | parse_confidence | parse_notes |
|---|---:|---|---|---:|---:|---|---|---|---|
| `Tab Metformin 500 mg BD` | 500.0 | mg | MASS | null | 2.0 | oral | false | HIGH | quantity per intake not stated |
| `Tab Metformin 500 mg 1-0-1` | 500.0 | mg | MASS | 1.0 | 2.0 | oral | false | HIGH | [] |
| `Tab Metformin 500 mg 2 tabs BD` | 500.0 | mg | MASS | 2.0 | 2.0 | oral | false | HIGH | [] |
| `Tab Atorvastatin 40 mg OD` | 40.0 | mg | MASS | null | 1.0 | oral | false | HIGH | quantity per intake not stated |
| `Tab Paracetamol 650 mg TDS` | 650.0 | mg | MASS | null | 3.0 | oral | false | HIGH | quantity per intake not stated |
| `Tab Dolo 650 TDS` | null | null | null | null | 3.0 | oral | false | HIGH | quantity per intake not stated |
| `Syp Paracetamol 5 ml BD for 1 week` | 5.0 | ml | VOLUME | null | 2.0 | oral | false | HIGH | quantity per intake not stated; volume/concentration note: cannot convert to mass |

Exact supplied patterns yielding `HIGH` with known intake quantity: `1-0-1` slot pattern and explicit number followed by dosage form (`2 tabs`). Those are the only two of the seven test inputs passing the conservative rule.

### Part C — Feasibility (evidence only)

- The parser reports strength, not taken amount.
- Daily total in a row's mass unit is computable without assuming one unit only when strength is mass, units per intake is explicit, frequency is known, and order is not PRN.
- `Tab Metformin 500 mg 1-0-1`: passes (500 mg × 1 × 2/day).
- `Tab Metformin 500 mg 2 tabs BD`: passes (500 mg × 2 × 2/day).
- Other five supplied lines fail: intake quantity is missing, strength is missing, or the value is volume rather than mass.
- The two passing parses demonstrate computability only; no label limit or dose decision is inferred.

### Part D — DailyMed label probe

Labels were fetched during this task. Each excerpt below is at most 25 words. “Maximum stated” is confined to the cited product/label and section; an OTC Directions section is identified where the label does not use a prescription-style Dosage and Administration heading. Formulation statements refer only to the specific listed product label, not all dosage forms for that medicine.

| Drug; product and setid | Explicit maximum in dosing section and excerpt | Variation by indication/formulation/renal function; age scope |
|---|---|---|
| Metformin; metformin hydrochloride film-coated tablet; `fc466c46-abaa-4675-aef2-4b1a1adfd912` | Yes, daily maximum: “up to a maximum dose of 2550 mg per day, given in divided doses.” | Indication: type 2 diabetes. Formulation: IR tablet label only. Renal: initiation/continuation restrictions apply. Adult maximum differs from pediatric maximum; label covers adults and ages 10+. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=fc466c46-abaa-4675-aef2-4b1a1adfd912) |
| Atorvastatin; atorvastatin calcium tablet; `0e24e7cb-1949-6686-e063-6394a90a4760` | Yes, daily range includes max: “The dosage range is 10 mg to 80 mg once daily.” | Indication/population and interacting medicines change dose caps. Formulation: tablet label only. Renal: no dose adjustment stated for renal impairment. Adult uses; ages 10+ for specified familial conditions. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0e24e7cb-1949-6686-e063-6394a90a4760) |
| Simvastatin; film-coated tablet; `db08460d-5184-42fa-8435-76eefa3569f5` | Yes, standard daily range: “The usual dosage range is 5 to 40 mg/day.” 80 mg is restricted to chronic tolerant use; co-medications impose lower caps. | Indication/population and interacting drugs change dose caps. Formulation: tablet label only. Renal: severe impairment starts 5 mg/day; mild/moderate needs no change. Adolescent HeFH ages 10–17 has its own range. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=db08460d-5184-42fa-8435-76eefa3569f5) |
| Lisinopril; tablet USP; `1d0caa63-9ea2-4a97-a23b-900a7c514bc6` | Yes, indication-specific daily maxima/ranges. Adult hypertension: “Titrate up to 40 mg daily based on blood pressure response.” | Indication-specific (hypertension, heart failure, MI); renal impairment changes initial dose. Formulation: tablet label (suspension also referenced for children needing lower dose). Pediatric hypertension ages 6+; other indications adult. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1d0caa63-9ea2-4a97-a23b-900a7c514bc6) |
| Digoxin; tablet; `dfac7f13-28be-423d-9389-9089da29da17` | No universal maximum stated; dosing section says “The maintenance dose is based on lean body weight, renal function, age, and concomitant products.” | Indication, age, lean body weight, renal function and concomitant products affect dose. Formulation: tablet label; solution directed for infants/young children/very low weight. Loading table ages 5–10 and over 10; label also includes adult indications. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=dfac7f13-28be-423d-9389-9089da29da17) |
| Ibuprofen; OTC 200 mg tablet; `265e2b47-d14a-45a8-adc0-7214e2057103` | OTC Directions section gives explicit tablet-count daily max, not mass: “do not exceed 6 tablets in 24 hours, unless directed by a doctor.” | Formulation: 200 mg OTC tablet only. Directions do not give indication- or renal-adjusted maxima; kidney disease prompts “ask a doctor.” Adults/children 12+; under 12 ask doctor. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=265e2b47-d14a-45a8-adc0-7214e2057103) |
| Acetaminophen; PAIN RELIEVER 500 mg film-coated caplet; `0c66b05d-132d-4c79-abfe-415fd68bbb9c` version 2 | Yes. Warning states: “The maximum daily dose of this product is 6 caplets (3000 mg) in 24 hours.” Directions separately cap count at six. | Formulation: 500 mg OTC caplet only. Maximum is product-specific, not indication-specific; liver disease warning is present. Adults/children 12+; under 12 do not use. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=0c66b05d-132d-4c79-abfe-415fd68bbb9c&version=2) |
| Aspirin; REGULAR STRENGTH ASPIRIN 325 mg coated tablet; `0fc3193d-af4e-ff3a-e063-6294a90a2743` | OTC Directions section gives tablet-count maximum, not mass: “not to exceed 12 tablets in 24 hours.” | Formulation: 325 mg OTC coated tablet only. Directions give product-count max; ask a doctor for kidney disease. Adults/children 12+; under 12 consult a doctor. [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0fc3193d-af4e-ff3a-e063-6294a90a2743) |

The label probe shows that several labels state daily maxima, sometimes in mass and sometimes in product counts. The prior B17a gate also required numeric `max_single_dose` and `max_daily_dose` fields in MASS units and specified age fields; daily-only maxima, tablet-count directions, and conditional/individualized limits could not be represented under that gate. Thus “zero staged” is explained by the combination of strict schema/prompt requirements and parser intake ambiguity, not by all labels lacking dosing limits.

## B16.2

### Part A — Clean copy

- Copy size: **8,555,245 bytes**.
- Exclusions: 27 paths, recorded in `reports/b162_excluded_paths.txt`. `.env` was excluded by name without being opened; `.env.example` was kept. Exclusions include `work/`, `.pytest_cache/`, `__pycache__/`, logs, and eight raw DDInter CSVs.
- Clean-copy seeded product data present: `rules.csv`, allergy/drug-disease/dose CSVs, drug classes and class rules. Raw DDInter source CSVs are absent.

### Part B — README and documented workflow commands

| Step | Result | Evidence / first output |
|---|---|---|
| `python -m pytest -q` | Exit 0; 301 passed, 1 skipped | One skip; tests pass without raw DDInter inputs. |
| `python -B scripts/run_demo.py` | Exit 0 | Demo reports deterministic output except timestamp and writes synthetic demo reports. |
| `python -m uvicorn medsafe.api.app:app --reload` | Started successfully; stopped with Ctrl+C after startup | Uvicorn logged “Application startup complete.” |
| README sample via `TestClient`, `use_llm=false` | Exit 0; HTTP 200 | Three expected checker findings (DDI, allergy, drug-disease) in synthetic payload. |
| `python scripts/validate_checker_csvs.py` (README data workflow) | Exit 0; 0 errors, 5 warnings | Warnings: the five drug-disease conditions are not in `conditions.csv`; no validation errors. |
| `python scripts/import_ddinter.py --output reports/ddinter_reimport/rules.csv` (optional README reproduction) | Exit 1 | `FileNotFoundError: No DDInter CSV files found` under `data/raw/ddinter`; intentionally excluded raw files must be downloaded first. |

### Part C — Findings

1. **Clean-copy tests:** 301 passed, 1 skipped. No test failures/errors. The skip is the existing opt-in live LLM test.
2. **Runtime data:** all required checked-in `data/seed/` CSVs are present without raw DDInter. The product test suite, demo and API operate from them.
3. **README step needing action:** optional import reproduction needs the eight raw DDInter download CSVs placed in `data/raw/ddinter/` as README instructs. No code change needed. The five validator warnings are schema-reference warnings, not errors; no fix was applied.
4. **NOTICE:** it says the filtered DDInter derivative is adapted/mapped, says distributed derivatives must preserve attribution/non-commercial terms and the same license, and names CC BY-NC-SA 4.0. It does not explicitly name the ML model as DDInter-derived/adapted. Thus NOTICE is **partially complete** against B16.2 Part C: derived rules are covered; model-specific wording is missing. No edit made.
5. **Clean-copy harness issue:** an initial copy helper mistakenly omitted project directories and yielded invalid “no tests/missing scripts” results. I discarded that copy, corrected the copy procedure, repeated the checks, and used only the corrected results above. A second API capture harness stalled because reload spawned a child process; that temporary copy was stopped and removed. The final controlled API startup and TestClient checks succeeded.
6. **Temp cleanup:** corrected clean-copy temp directory deleted.
7. No source, model, data, script, or existing report was edited; no dose rows staged; no B17b/B18 run.
