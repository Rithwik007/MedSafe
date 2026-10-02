# B9 anecdotal model-output checks

Checked 2026-09-30 against public interaction sources and one official label. These are six spot checks, not validation and not clinical guidance. “No interaction found” is not proof that no interaction exists. Severity categories from external checkers may differ from DDInter.

| DDInter Unknown pair | ML estimate | Spot-check | Source |
|---|---|---|---|
| Potassium chloride + sertraline | Major (0.9135) | Disagree / unsupported: source reports no known interaction between potassium and sertraline. | [HelloPharmacist interaction lookup](https://hellopharmacist.com/drug-supplement-interactions/drug-herbal/potassium-with-sertraline) |
| Phenytoin + simvastatin | Major (0.9009) | Disagree on Major severity: the pair checker found no interaction, while the phenytoin monograph says phenytoin can lower simvastatin concentrations and dosage adjustment may be needed; the cited sources do not call this Major. | [Drugs.com pair checker](https://www.drugs.com/drug-interactions/phenytoin-sodium-with-simvastatin-1863-15957-2067-0.html?professional=1), [Drugs.com phenytoin monograph](https://www.drugs.com/monograph/phenytoin-phenytoin-sodium.html?references=1), [DailyMed phenytoin label](https://www.dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=d4459837-da26-4c97-8587-32eb1f682d58) |
| Levothyroxine + prednisolone | Moderate (0.9010) | Agree: Drugs.com classifies this pair as Moderate and recommends monitoring. | [Drugs.com interaction report](https://www.drugs.com/interactions-check.php?drug_list=1463-0%2C1933-0&professional=1) |
| Metformin + acetylsalicylic acid | Moderate (0.9146) | Disagree / unsupported: Drugs.com reports no interaction found for metformin + aspirin. | [Drugs.com interaction report](https://www.drugs.com/drug-interactions/aspirin-with-metformin-243-0-1573-0.html?professional=1) |
| Acetaminophen + clarithromycin | Minor (0.9728) | Disagree / unsupported: Drugs.com reports no interaction found for acetaminophen + clarithromycin. | [Drugs.com interaction report](https://www.drugs.com/drug-interactions/clarithromycin-with-tylenol-685-0-11-12.html?professional=1) |
| Doxycycline + clopidogrel | Minor (0.9762) | Disagree / unsupported: Drugs.com reports no interaction found for this pair. | [Drugs.com interaction report](https://www.drugs.com/drug-interactions/clopidogrel-with-doxy-d-705-0-940-2646.html) |

Four predictions were not supported by the selected pair-specific checker, one severity was unsupported despite pharmacokinetic interaction evidence, and one Moderate prediction agreed with the source classification. This small check highlights why estimates remain unverified and review-required.
