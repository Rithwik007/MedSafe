# DDInter full-graph data audit

Source: local DDInter CSV files in `data/raw/ddinter/`; no network access used.
Pairs are canonicalized by case-insensitive drug name. Duplicate pairs retain highest listed severity.

## Counts

- Total rows read: 222,383
- Unique canonical pairs: 160,235
- Unique drugs: 1,939
- Unique labeled pairs: 130,422
- Unknown share of unique pairs: 18.61%
- Whitelist drugs present: 30/30

## Raw rows by label

| Raw label | Rows |
|---|---:|
| Major | 33,896 |
| Minor | 10,938 |
| Moderate | 130,367 |
| Unknown | 47,182 |

## Deduplicated unique pairs by label

| Label | Pairs |
|---|---:|
| Major | 26,914 |
| Moderate | 96,675 |
| Minor | 6,833 |
| Unknown | 29,813 |

## Duplicate severity conflicts: 0

Every conflicting pair was logged during loading. First 10 examples:

| Drug A | Drug B | Labels seen | Kept |
|---|---|---|---|

## Whitelist drugs found

Warfarin, Acetylsalicylic acid, Ibuprofen, Metformin, Lisinopril, Amoxicillin, Clarithromycin, Simvastatin, Sertraline, Tramadol, Acetaminophen, Furosemide, Atorvastatin, Clopidogrel, Digoxin, Fluconazole, Ciprofloxacin, Azithromycin, Omeprazole, Pantoprazole, Levothyroxine, Carbamazepine, Phenytoin, Diazepam, Codeine, Potassium chloride, Spironolactone, Doxycycline, Prednisolone, Benzylpenicillin
