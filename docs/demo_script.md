# MedSafe synthetic demo script

Run from the project directory with the API at localhost. UI examples use the same inputs as scripts/run_demo.py. No real patient information is used.

## Scenario 1 — duplicate and DDI findings

Patient fields: leave blank.

Prescription:

    Combiflam
    Dolo 650
    Warfarin

Expected findings copied from reports/demo/demo_1.txt: DDINTER-DDInter1951-DDInter900 (MAJOR), DDINTER-DDInter14-DDInter1951 (MODERATE), DUPLICATE-POLICY-INGREDIENT (MODERATE), and DDINTER-DDInter14-DDInter900 (UNSPECIFIED). The result includes an ML-PREDICTED estimate only where the API returns one.

## Scenario 2 — label rows

Allergies: amoxicillin

Diagnoses, one per line: myasthenia gravis; adrenal insufficiency

Prescription:

    Amoxicillin
    Ciprofloxacin

Expected findings copied from reports/demo/demo_2.txt: B14-ALG-001 and B14-DIS-004; the DDI output is also shown in the saved report. The unmatched adrenal insufficiency input stays under unresolved items.

## Scenario 3 — unresolved input and ML annotation

Patient fields: leave blank.

Prescription:

    mystery syrup xyz 7-3-1
    Lisinopril
    Levothyroxine

Expected output copied from reports/demo/demo_3.txt: the mystery text remains unresolved; the Lisinopril and Levothyroxine DDI finding stays UNSPECIFIED and carries an explicitly unverified ML note.

## 60-second talk track

“MedSafe takes synthetic prescription text and compares supported inputs with its local, source-tracked rules. This example shows a duplicate-ingredient policy finding alongside DDI rows. The checker labels show the amount of data behind each result. Some source rows have no severity, so those findings remain UNSPECIFIED. The model can add an unverified estimate to eligible rows, while Major estimates are withheld under the frozen B13 rule. Unparsed or unmatched text remains visible. The dose checker covers one label row and only adult single-order cases. These outputs need pharmacist review and are not for clinical use.”

## Fallback

If the live UI is unavailable, open reports/demo/demo_1.txt, reports/demo/demo_2.txt, reports/demo/demo_3.txt, reports/demo/dose_over_limit.txt and reports/demo/dose_missing_age.txt. Screenshots were not taken; the local UI route evidence is in reports/b19_ui_server_evidence.json.

## Limits for Q and A

- 174 of 313 DDI rules have no source severity.
- ML estimates are unverified; Major estimates are withheld.
- Disease matching is exact phrase only.
- Dose coverage is one source-text-checked adult row; checks require a known single-order quantity, frequency and route. Co-medication-specific lower caps are not encoded.
- Label source text was checked, not clinically reviewed.
- Live LLM measurement accepted 0 of 25 parser cases and 0 of 15 summaries; no acceptance threshold was set.
