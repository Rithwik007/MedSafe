# Checker CSV data entry

These files define input schemas only. Shipped allergy, drug-disease, and dose files contain headers and no clinical rows.

- `match_type` (allergy): `DIRECT` means drug or ingredient is itself the allergen. `CROSS_REACTIVITY` means source label links an allergen class to this drug.
- `label_category`: use `CONTRAINDICATION`, `WARNING`, or `PRECAUTION`, exactly as the source label classifies it.
- `reason` and `recommendation`: paraphrase label wording; do not copy it.
- Dose rows: adult band only (`population=ADULT`) for now. Use single-ingredient drugs only. Leave `per_kg_basis` and `renal_note` blank when not applicable.
- `accessed_on`: ISO date source was read. `verified_on`: ISO date reviewer checked row. A row is reviewed only when both `reviewed_by` and `verified_on` are non-blank.
- Every clinical row needs `source_name`, `source_url`, and exact `source_section`. Keep unsure rows out.

Severity mappings for allergy and drug-disease categories are design decisions recorded only in `severity_policy.csv`; they are not clinical grading.
