# B14 Part A — schemas and engine inputs

## Exact CSV headers

From `CHECKER_COLUMNS` in `medsafe/checkers/stubs.py`:

- `allergy_rules.csv`: `rule_id,drug,allergen,match_type,label_category,reason,recommendation,source_name,source_url,source_section,accessed_on,reviewed_by,verified_on`
- `drug_disease_rules.csv`: `rule_id,drug,condition,label_category,reason,recommendation,source_name,source_url,source_section,accessed_on,reviewed_by,verified_on`
- `dose_limits.csv`: `rule_id,drug,route,population,age_min_years,age_max_years,dose_unit,max_single_dose,max_daily_dose,per_kg_basis,renal_note,source_name,source_url,source_section,accessed_on,reviewed_by,verified_on`

The schema guide is `data/seed/README_checker_csvs.md`. It says allergy `match_type` is `DIRECT` or `CROSS_REACTIVITY`; label categories are `CONTRAINDICATION`, `WARNING`, or `PRECAUTION`; dose rows are adult-only, single-ingredient; every clinical row needs source name, URL, section, and access date; reviewer and verification fields jointly determine review status.

## Validator rules relevant to staged rows

`REQUIRED_COMMON`: `rule_id,drug,source_name,source_url,source_section,accessed_on`. Allergy additionally requires `allergen,reason,label_category`; disease requires `condition,reason,label_category`. Allergy match type must be `DIRECT` or `CROSS_REACTIVITY`; categories must occur in `severity_policy.csv`; drug must resolve by exact curated match. Dose requires positive single and daily amounts, daily ≥ single, mass unit listed in `units.csv`, `population=ADULT`, numeric `age_min_years < age_max_years`, and an exact single-ingredient drug. Reviewer/date must both be blank or both set. The validator has no repository-path option, so Part C uses a temporary repo copy.

## Whitelist and actual checker capability

The 30 curated whitelist entries are: Warfarin; Acetylsalicylic acid; Ibuprofen; Metformin; Lisinopril; Amoxicillin; Clarithromycin; Simvastatin; Sertraline; Tramadol; Acetaminophen; Furosemide; Atorvastatin; Clopidogrel; Digoxin; Fluconazole; Ciprofloxacin; Azithromycin; Omeprazole; Pantoprazole; Levothyroxine; Carbamazepine; Phenytoin; Diazepam; Codeine; Potassium chloride; Spironolactone; Doxycycline; Prednisolone; Benzylpenicillin.

The local normalizer can resolve exact curated names for all 30. **The three clinical checker implementations currently match none of them:** `engine.analyze()` calls `stub_status()` for ALLERGY, DRUG_DISEASE, and DOSE. `stubs.py` only counts reviewed source rows; it explicitly says checker logic is not implemented. Staged rows are research material and will not trigger findings, even after promotion until checker logic is implemented.

## Engine input fields and support

`Patient` has `allergies: list[str]`, `diagnoses: list[str]`, `age`, `weight_kg`, and `egfr`. `MedOrder` has `dose_value`, `dose_unit`, `unit_kind`, `frequency_per_day`, `route`, `units_per_intake`, and related fields. Its model documentation defines dose value/unit as product strength as written, not dose per intake. The data schema accepts a condition string; the project `conditions.csv` has headers only. So the input fields exist, but the checkers do not use them yet.

The dose schema also requires a finite numeric age minimum and maximum. The DailyMed adult dosage labels examined below describe adults but do not state a maximum age; filling an arbitrary upper age would invent an applicability limit. Therefore no dose candidate is staged. This is a schema/source mismatch, not evidence that no numeric dosage limits exist.
