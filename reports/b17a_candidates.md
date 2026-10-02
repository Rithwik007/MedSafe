# B17a candidate assessment (2026-10-02)

No rows kept. B17a requires an explicit source-stated numeric maximum and unit, and the existing validator requires numeric values for both maximum fields, a MASS unit, population exactly `ADULT`, and numeric age bounds. B17a also requires adult wording with blank age bounds when the label gives no age range. No candidate can be represented without deriving a mass value, inventing a single-dose limit, or violating those stated constraints. The staging CSV is header-only.

| Candidate | Disposition | Reason |
|---|---|---|
| Acetaminophen (OTC) | Skipped | Label directions give caplet counts per interval and per 24 hours. The maximum is not directly stated in a mass unit; converting caplet counts using product strength is disallowed. Single-dose mass maximum also is not stated directly. |
| Ibuprofen (OTC) | Skipped | Label gives tablet counts and frequency, not maximum single/daily dose directly in a mass unit. Converting counts by strength is disallowed. |
| Metformin | Skipped | Prescription limits are indication/titration/renal-context dependent; label maximum daily value does not supply an explicit matching single-dose maximum. |
| Atorvastatin | Skipped | Label dosage range/max is daily and context-dependent; no explicit maximum single-dose in mass unit, and an adult-only row with blank ages conflicts with current validator. |
| Simvastatin | Skipped | Label limits vary by indication and interacting therapy; no single universal row satisfying the prompt and current validator. |
| Aspirin (acetylsalicylic acid) | Skipped | OTC label gives tablet counts and interval, not maximum mass values directly. Conversion by tablet strength is disallowed. |
| Lisinopril | Skipped | Label dosage depends on indication and titration; no direct maximum single-dose field satisfying the row schema. |
| Digoxin | Skipped | Label dosing is individualized by age, lean body weight, renal function and titration; no universal numeric maximum row satisfying the prompt. |

No staged rows means there were no row excerpts to verify or reviewer fields to populate. The addendum request to set reviewer identity is also barred by B17a's explicit self-review prohibition. B17b was not performed.
