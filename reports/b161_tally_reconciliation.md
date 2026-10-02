# B16.1 Part A: B12 tally reconciliation

## Files and pair counts

| File | Rows | Unique pairs | Role |
|---|---:|---:|---|
| `reports/ml_spotcheck.csv` | 18 | 18 | Main B10.2 worksheet |
| `reports/ml_spotcheck_kcl.csv` | 5 | 5 | KCl appendix |
| `reports/b12_pass1_blind.csv` | 25 | 25 | Blind copy of 25 scoped pairs; 23 overlap main + appendix and 2 are not in those two source sheets |
| `reports/ml_spotcheck_filled.csv` | 25 | 25 | Filled combined B12 worksheet; tally source |
| `reports/ml_spotcheck_b10_1.csv` | 16 | 16 | Older B10.1 worksheet; historical, separate sample |

The 18-row main sheet and 5-row appendix have no overlap: 23 unique pairs total. The blind/filled B12 sheets add two more pairs: `diazepam + potassium chloride` and `potassium chloride + sertraline`, yielding the reconciled scope of 25 unique pairs. The B10.1 sheet is a prior sample and is not additive to B12.

## Why 29 appeared

`reports/b13_decision_outcome.md` recorded `1 agree + 1 disagree + 23 unclear + 4 not retrievable = 29`. The four not-retrievable pairs are already marked `unclear` in the `agrees` column of `reports/ml_spotcheck_filled.csv`, so adding them again double-counted those four rows. The actual sheet contains 25 unique data rows.

The tally script has no `not_retrievable` category. Its category mapping treats the `agrees` cell literally and therefore assigns these four rows to `unclear`; the not-retrievable status lives in `source_result`. Relevant code in `scripts/tally_spotcheck.py`:

```python
CATEGORIES = ("agree", "disagree", "unclear", "unfilled", "invalid")
...
value = (row.get("agrees") or "").strip().casefold()
category = value if value in {"agree", "disagree", "unclear"} else (
    "unfilled" if not value else "invalid")
```

Lines 10 and 22–24. The mismatch is a reporting double count, not a header, duplicate pair, or extra data row. No tally script or earlier report was edited.

## Corrected B12 result

Mutually exclusive categories, using `source_result=not_retrievable` to separate unavailable source checks from other unclear outcomes:

| Outcome | Count |
|---|---:|
| Unique pairs checked | 25 |
| Agree | 1 |
| Disagree | 1 |
| Unclear (excluding not retrievable) | 19 |
| Not retrievable | 4 |
| Major pairs with definite answer | 0 of 9 |

The nine Major-labeled pairs all have `agrees=unclear`; two are marked not retrievable. Thus none meets the frozen definite-answer rule. Major ML notes remain suppressed. This limited spot check does not establish model performance or clinical validity.

