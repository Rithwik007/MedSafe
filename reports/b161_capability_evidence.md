# B16.1 capability evidence refresh

Synthetic-only evidence. API capability calls and the fake LLM call were re-run locally. All three synthetic demo cases were run three times; each was deterministic except for `generated_at` and matched its B16 snapshot after excluding only that timestamp. Full text and comparison files are `reports/b161_demo_1.txt` through `reports/b161_demo_3.txt` and matching `_comparison.txt` files.

| # | Capability | Current observed evidence | Product status (exact) |
|---:|---|---|---|
| 1 | Free-text prescription parsing | Five parser inputs parsed: Combiflam BD=2/day; Dolo 650 TDS=3/day; Crocin Advance 500 OD=1/day; Brufen 200 SOS (`as_needed=true`); Amoxicillin 1-0-1=2/day. | Parsed; no checker status |
| 2 | DDI findings | Synthetic API case emitted rule `DDINTER-DDInter1951-DDInter900` at MAJOR and associated MODERATE/UNSPECIFIED findings. | `PARTIAL` |
| 3 | Duplicate medication | Combiflam + Dolo 650 emitted `DUPLICATE-POLICY-INGREDIENT`, MODERATE. | `RAN` |
| 4 | Allergy conflict | Amoxicillin exact match emitted `B14-ALG-001`, UNSPECIFIED. | `PARTIAL` |
| 5 | Drug-disease finding and unresolved condition | Ciprofloxacin + myasthenia gravis emitted `B14-DIS-004`, UNSPECIFIED; adrenal insufficiency remained unresolved due exact-phrase matching. | `PARTIAL` |
| 6 | Dose-limit checks | No dose rows are loaded; no dose finding emitted. | `NOT_RUN_NO_DATA` |
| 7 | Explainable report and REST API | Current synthetic POST returned HTTP 200 with findings, evidence, statuses, and unresolved items. | `1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA` |
| 8 | ML note and withheld estimate | Three demos re-run with local checksum-verified model. One unspecified pair carried a Minor `ML-PREDICTED (unverified)` note; earlier evidence records fake Major estimate withholding and the 9 withheld count. | `ENABLED` |
| 9 | Optional LLM layer (fake client only) | Fake fallback accepted one extraction: attempted=1, accepted=1, rejected=0; resulting order was MEDIUM confidence, `BD`, `llm_assisted=true`. No provider call or API key used. | `DISABLED` by default; fake opt-in invocation accepted |

The consolidated checker status string printed by the product is `1 RAN, 3 PARTIAL, 1 NOT_RUN_NO_DATA`. The five checker statuses are DDI `PARTIAL`, duplicate `RAN`, allergy `PARTIAL`, drug-disease `PARTIAL`, and dose `NOT_RUN_NO_DATA`. ML `ENABLED` and LLM `DISABLED` are displayed separately.
