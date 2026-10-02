# B14 Part B — candidate disposition

Access date for fetched sources: 2026-10-02. All source URLs below are DailyMed. No Drugs.com, forums, blogs, or LLM-generated sources used. Staged rows are drafts, not clinically verified.

## Allergy candidates

| Candidate | Decision | Basis |
|---|---|---|
| Amoxicillin — amoxicillin hypersensitivity | Kept (`B14-ALG-001`) | Section 4 explicitly contraindicates after serious hypersensitivity to amoxicillin. |
| Ibuprofen — ibuprofen hypersensitivity | Kept (`B14-ALG-002`) | Contraindications section explicitly names known hypersensitivity to ibuprofen. |
| Ciprofloxacin — ciprofloxacin hypersensitivity | Kept (`B14-ALG-003`) | Section 4.1 explicitly names ciprofloxacin hypersensitivity. |
| Fluconazole — fluconazole hypersensitivity | Kept (`B14-ALG-004`) | Contraindications explicitly name hypersensitivity to fluconazole. Cross-azole claims deliberately excluded. |
| Azithromycin — azithromycin hypersensitivity | Kept (`B14-ALG-005`) | Section 4.1 explicitly names azithromycin hypersensitivity. |

## Drug-disease candidates

| Candidate | Decision | Basis |
|---|---|---|
| Levothyroxine — uncorrected adrenal insufficiency | Kept (`B14-DIS-001`) | Section 4 explicitly contraindicates use in this condition. |
| Azithromycin — history of cholestatic jaundice/hepatic dysfunction associated with prior azithromycin use | Kept (`B14-DIS-002`) | Section 4.2 explicitly states the contraindication with this drug-specific history. |
| Ibuprofen — CABG surgery setting | Kept (`B14-DIS-003`) | Contraindications explicitly state ibuprofen is contraindicated in the setting of CABG surgery. |
| Ciprofloxacin — myasthenia gravis | Kept (`B14-DIS-004`) | Section 5.5 says it may exacerbate muscle weakness and says to avoid it with known history. |
| Amoxicillin — mononucleosis | Kept (`B14-DIS-005`) | Section 5.4 states rash occurs in a high percentage of patients with mononucleosis who receive amoxicillin and says not to administer it to them. |

The disease-condition names are not present in `data/seed/conditions.csv` (currently header-only); the validator is expected to report condition-map warnings. The rows are explicit label text, but the app has no current condition matching logic.

## Dose candidates examined and skipped

| Candidate | Source limit located | Decision and reason |
|---|---|---|
| Codeine sulfate tablets, adults | 15–60 mg per dose, maximum 360 mg/24 hours; DailyMed section 2.2. | Skipped: the source says “adult” but gives no maximum age. Validator requires numeric minimum and maximum ages, so a finite upper bound would be invented. |
| Tramadol immediate-release tablets, adults 17+ | 50–100 mg per dose, maximum 400 mg/day; renal/geriatric modifications also stated; DailyMed section 2.3. | Skipped: age minimum is explicit, but label gives no maximum age; validator requires one. A blanket row would also omit the label’s patient-specific adjustments. |
| Ibuprofen tablets | Label gives single doses up to 800 mg and maximum daily dose 3200 mg; DailyMed section 2. | Skipped: examined label does not give the finite adult age range required by validator. |
| Acetaminophen IV | Label’s cited dosing group includes adults and adolescents with a weight threshold. | Skipped: mixed population does not fit the current `population=ADULT` schema without interpretation. |

No dose row was staged rather than fabricate an age limit or translate the mixed population. Consequently `dose_limits.csv` contains its exact header and zero data rows.

## Source URLs consulted

- Amoxicillin allergy and mononucleosis: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=641ec2a8-368a-4c5c-8c11-37366a06ce93 and https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid=a3b98df9-eddc-441a-84dd-51bc5f8dc6e4&type=pdf
- Ibuprofen allergy, CABG, and dose: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2e0f74a5-b8f3-fc81-e063-6394a90a647a and https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=70e191ef-8fad-49eb-9850-fceea119e92f
- Ciprofloxacin allergy and myasthenia gravis: https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b283d662-9be1-49c7-be03-cb21055314c1
- Fluconazole allergy: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=4eaf5b04-c026-4a49-879f-2925b375f903
- Azithromycin allergy and hepatic dysfunction: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=397471e5-76e2-462c-af30-bcc54fe00266
- Levothyroxine adrenal insufficiency: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=853d9e86-2b5b-4967-8c22-70ad34f03418
- Codeine dose: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f317cd06-2851-4a52-86d3-6efde3a4c243
- Tramadol dose: https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=58c2975a-47bd-4d3c-9cfe-9ea59f3f31ca
