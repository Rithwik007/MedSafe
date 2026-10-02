# B13 exposure check

Date: 2026-10-01

Re-scored all 174 `UNSPECIFIED` DDI rules with checksum-verified local artifacts and frozen tau. `WITHHOLD_MAJOR_ESTIMATES` remained enabled. No retraining, network access, LLM calls, or CSV edits.

| Outcome | Count |
|---|---:|
| Estimates withheld pending outside review | 9 |
| Moderate estimates | 35 |
| Minor estimates | 68 |
| Below tau | 62 |
| Total | 174 |

All 9 outputs previously labeled Major now have no ML prediction and no ML note. The 62 below-tau rows also have no ML prediction. Moderate and Minor notes remain attached. Serving status reports only `9 estimates withheld pending outside review`; it does not expose the withheld class.
