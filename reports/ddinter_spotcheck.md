# DDInter live detail spot-check

Checked five imported whitelist pairs against DDInter interaction detail pages on 2026-09-30. Names and risk levels matched CSV-derived rules in all five checks. This verifies source page agreement, not clinical correctness.

| Pair | CSV severity | DDInter detail result | Source |
|---|---|---|---|
| Tramadol + Clarithromycin | MODERATE | Moderate; Synergy | https://ddinter.scbdd.com/ddinter/interact/953108/ |
| Ciprofloxacin + Simvastatin | MODERATE | Moderate; Metabolism | https://ddinter.scbdd.com/ddinter/interact/1013641/ |
| Spironolactone + Warfarin | MINOR | Minor; Antagonism | https://ddinter.scbdd.com/ddinter/interact/1006791/ |
| Digoxin + Levothyroxine | MODERATE | Moderate; Metabolism | https://ddinter.scbdd.com/ddinter/interact/1034059/ |
| Warfarin + Ibuprofen | MAJOR | Major; Synergy | https://ddinter.scbdd.com/ddinter/interact/957806/ |

DDInter severity was checked on its live interaction detail view. DDInter is still an upstream dataset, not an independent clinical gold standard. Keep imported rows marked not independently clinically reviewed.
