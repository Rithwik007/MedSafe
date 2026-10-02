# B19 Phase 2 dose candidate screen — 2026-10-02

Staged rows: 1. Files: `reports/b19_staging/dose_limits.csv` and `reports/b19_staging/excerpts.csv`. The excerpt is 10 words. Reviewer fields are blank. No row was promoted.

| Candidate | Decision | Evidence and reason |
|---|---|---|
| Metformin | Skip | DailyMed IR tablets setid `fc466c46-abaa-4675-aef2-4b1a1adfd912` has an adult maximum of 2550 mg/day divided; ER label setid `cc070735-5e8d-4bb3-9caa-e84d29bb8943` has an up-to-2000 mg/day once-daily regimen. Formulations have different limits; prompt says skip. [IR label](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=fc466c46-abaa-4675-aef2-4b1a1adfd912), [ER label](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=cc070735-5e8d-4bb3-9caa-e84d29bb8943) |
| Atorvastatin | **Stage** `B19-DOSE-ATORVASTATIN-001` | Prescription tablet label section 2.2 says “The dosage range is 10 mg to 80 mg once daily.” This provides a daily and single-dose 80 mg adult ceiling for this tablet product. The label also lists lower co-medication-specific caps; this staged general ceiling does not encode those. Reviewer must check the exact product, 80 mg, once-daily frequency, adult population and co-medication caveat. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0e24e7cb-1949-6686-e063-6394a90a4760) |
| Simvastatin | Skip | Dosage caps vary with interacting drugs; severe renal impairment has a lower starting dose. Does not meet the context-independent rule. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=db08460d-5184-42fa-8435-76eefa3569f5) |
| Lisinopril | Skip | Limits vary by indication and renal function; pediatric dosing also differs. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1d0caa63-9ea2-4a97-a23b-900a7c514bc6) |
| Digoxin | Skip | Label individualizes maintenance by age, lean body weight, renal function and concomitant products; no universal mass/day maximum. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=dfac7f13-28be-423d-9389-9089da29da17) |
| Ibuprofen | Skip | OTC 200 mg tablet label gives a product-specific tablet-count cap, not a prescription mass maximum; OTC labels are excluded. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=265e2b47-d14a-45a8-adc0-7214e2057103) |
| Acetaminophen | Skip | OTC 500 mg caplet label has a product-specific 6-caplet/3000 mg ceiling; OTC limits are excluded. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=0c66b05d-132d-4c79-abfe-415fd68bbb9c&version=2) |
| Aspirin | Skip | OTC 325 mg coated tablet label gives tablet counts per interval/24 hours; product-specific OTC limit excluded. [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0fc3193d-af4e-ff3a-e063-6294a90a2743) |

Source-text verification was performed by Codex after the owner authorized completing the gate. The label title, prescription classification, adult dosage section, 80 mg ceiling, once-daily frequency, and lower co-medication-specific caps were checked. Reviewer provenance is recorded as Codex, not attributed to the owner. This was source-text checking only, not clinical review.

The promoted data/seed/dose_limits.csv row uses 80 mg for both single and daily maximum. D1 permits the label wording “adults (age range not stated by label)” with both age cells blank. The validator now accepts this convention.

Phase 2 pytest after staging: 301 passed, 1 skipped.
