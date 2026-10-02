# B17a Part A: schema and parser findings

## Exact `dose_limits.csv` header

`rule_id,drug,route,population,age_min_years,age_max_years,dose_unit,max_single_dose,max_daily_dose,per_kg_basis,renal_note,source_name,source_url,source_section,accessed_on,reviewed_by,verified_on`

## Validator rules for dose rows

The validator requires all schema columns; flags unknown columns; requires common source fields (`rule_id`, `drug`, `source_name`, `source_url`, `source_section`, `accessed_on`) to be nonblank; requires valid nonfuture ISO dates when present; requires `reviewed_by` and `verified_on` either both blank or both set; requires the drug to resolve by exact curated match and be a single ingredient; requires `max_single_dose` and `max_daily_dose` positive numeric values, daily >= single; requires `dose_unit` to be a MASS unit listed in `units.csv`; requires `population` exactly `ADULT`; and requires numeric age bounds with minimum < maximum. It detects duplicate drug/population identities. `renal_note` and `per_kg_basis` are not separately required by the current dose-row validator.

## Parser order fields and exact meaning

| Field | Meaning |
|---|---|
| `dose_value` | Product strength as written, not dose per intake. |
| `dose_unit` | Unit attached to that strength. |
| `unit_kind` | Whether strength is mass, volume, or IU; volume/IU cannot be compared to mass limits. |
| `frequency_per_day` | Parsed numeric frequency per day, nullable when not resolved. |
| `units_per_intake` | Number of product units per intake; `None` means quantity per intake was not stated or resolved. |
| `route` | Parsed or form-derived route; a separate flag records when route was assumed. |
| `as_needed` | Whether order was parsed as as-needed (for example SOS). |
| `parse_confidence` | `HIGH`, `MEDIUM`, or `LOW`; high requires resolved drug, recognized strength/brand, frequency, no leftovers/conflicts/ambiguity. |

When amount-per-intake is meaningful, it is product strength × `units_per_intake`; the model documentation says not to use that calculation for combination products. The model also has `one_time`.

## Age field

The patient model has `Patient.age` (`int | None`, constrained 0–120). No age field appears on the prescription request model itself.

## Dolo 650

`Dolo 650` is a curated brand alias resolving to ingredient `paracetamol`. The synonym record describes it as a 650 mg tablet product and explicitly says strength is not used as a dose recommendation. Parser brand handling recognizes a brand-plus-number token; this does not make that product strength a dose limit or a per-intake amount.
