# B13 decision outcome

Date: 2026-10-01

## B12 tally

Recorded outside-source review: 1 agree, 1 disagree, 23 unclear, and 4 not retrievable. Among 9 model outputs labeled Major, 0 had a definite answer. The rule requires at least 3 definite Major rows. Therefore, the outcome is **suppress Major ML notes**.

## Frozen rule (quoted)

> Only rows with agrees = agree or disagree are "definite". Unclear is excluded from the denominator but reported.
> Major ML notes stay on only if at least 3 Major rows are definite AND at least half of the definite Major rows agree. Otherwise suppress Major ML notes.
> Moderate and Minor: report counts only. No action.

## Serving policy

`WITHHOLD_MAJOR_ESTIMATES = True` applies this decision after prediction and before an ML note is attached. It does not change model artifacts, tau, rule-based findings, finding severity, order, or presence. The user-facing status reports only the number withheld and says “estimate withheld pending outside review.”

This is a limited spot check, not a validation study. Unclear rows do not count as agreement. No accuracy claim follows from this tally.
