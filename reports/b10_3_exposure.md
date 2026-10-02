# B10.3 deployed exposure

Source: 313 DDI rules loaded from local checker knowledge base. Shipped model loaded with local SHA-256 verification. Model, threshold, and clinical CSVs unchanged. No network or LLM calls.

## UNSPECIFIED rules (174)

| Outcome | Count |
|---|---:|
| Major estimate | 9 |
| Moderate estimate | 35 |
| Minor estimate | 68 |
| Abstained: below tau | 62 |
| Abstained: unknown drug | 0 |
| Abstained: pair already labeled | 0 |
| Abstained: pair not listed by DDInter | 0 |
| Total | 174 |

Eight of 9 Major estimates involve potassium chloride.

### UNSPECIFIED rules with Major estimate

Pair names only; estimates remain ML-PREDICTED and unverified.

- acetaminophen + potassium chloride
- phenytoin + potassium chloride
- phenytoin + simvastatin
- azithromycin + potassium chloride
- potassium chloride + sertraline
- potassium chloride + tramadol
- carbamazepine + potassium chloride
- diazepam + potassium chloride
- furosemide + potassium chloride

## All loaded DDI rules (313)

- Rules receiving an ML note: 112 (9 Major, 35 Moderate, 68 Minor).
- Remaining 201: 139 already have classified severity and 62 UNSPECIFIED rules abstain below tau.

Abstention counts use predictor's checks in order: unknown drug, pair not in model's listed-pair set, pair not in model's unlabeled-pair set, then below tau after scoring. No other abstention reasons occurred.
