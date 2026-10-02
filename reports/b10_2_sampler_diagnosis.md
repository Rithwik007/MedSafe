# B10.2 sampler diagnosis

## Candidate pool counts and filter order

| Class | All covered DDInter Unknown pairs | After whitelist filter (both drugs) | After two-pairs-per-drug cap | Final selected |
|---|---:|---:|---:|---:|
| Major | 734 | 9 | 3 | 3 |
| Moderate | 12,894 | 35 | 7 | 7 |
| Minor | 6,818 | 68 | 6 | 6 |

Filter order: score all DDInter Unknown pairs at the shipped threshold; require both pair members in the 30-drug whitelist; then apply the per-drug cap while filling class quotas. Counts after the cap are from the seeded B10.1 selection (requested 7/7/6).

## What the cap counts

The cap counts only the pair's own two drugs: selection checks both members of each candidate pair and increments each member's count. Candidate filtering at `scripts/export_ml_spotcheck.py:53` requires both drugs to be whitelist members. Thus every partner counted in the old worksheet is itself a whitelist drug.

## How the previous rows were chosen

B10.1 sorted candidate pairs for reproducible input order, initialized `random.Random(seed)`, and called `rng.shuffle(candidates)` at `scripts/export_ml_spotcheck.py:19,24-27`. Rows were seeded random order, not top-probability or first-N.

## Root cause of three Major selections

This was a pool restriction combined with the per-drug cap, not a bug in the cap implementation. The global model has 734 Major estimates, but the old worksheet pool required both drugs to be among the 30 whitelist drugs; only 9 Major candidates remained. Eight of those nine contain potassium chloride, while the only non-potassium-chloride candidate is phenytoin + simvastatin. Under the two-pair cap, potassium chloride can contribute at most two candidates; phenytoin + simvastatin adds one, so at most three Major candidates can be selected. The cap also explains why the requested Major quota could not be filled.

## Touch count

TEST_SPLIT_TOUCH: 0.

