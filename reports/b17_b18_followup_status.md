# B17a / B18 gate status

## B17a staged rows

`reports/b17_staging/dose_limits.csv` contains only the header:

```csv
rule_id,drug,route,population,age_min_years,age_max_years,dose_unit,max_single_dose,max_daily_dose,per_kg_basis,renal_note,source_name,source_url,source_section,accessed_on,reviewed_by,verified_on
```

`reports/b17_staging/excerpts.csv` contains only its header:

```csv
rule_id,source_excerpt
```

B17a staged zero eligible rows. There are no rows for the owner to verify and no reviewer fields were populated.

## Gate

B17b has not been run or accepted. The B17b instructions say to stop if no rows are promoted. Therefore B18 remains deferred under the supplied sequencing instruction (“B18 can wait until B17b is accepted”). No Groq provider, `.env` loader, live measurement, zip tool, or B18 docs/tests were implemented in this step. The real `.env` file was not opened or read.

## Completed now from the B16.1 verdict

- Added reproducible DDInter download/import instructions to README, including a separate output path so a re-import does not overwrite the checked-in CSV.
- Added `NOTICE` with DDInter attribution, source and terms links, license, derivative-data disclosure, and non-commercial/share-alike notes.
- Added ignore rules for the eight raw DDInter CSV files and `work/b9_repro_20260930/`; kept `data/raw/ddinter/SOURCE.md` visible.
- No raw source dumps or reproduction archive were deleted. No source data, model, application code, or API keys were changed.

Official references checked: [DDInter download page](https://ddinter.scbdd.com/download/) and [DDInter terms](https://ddinter.scbdd.com/terms/). The terms page states CC BY-NC-SA 4.0 and limits downloads to personal, non-commercial, informational, or scholarly use.

## Verification for this follow-up

- Pytest after README, NOTICE, and ignore-rule edits: 301 passed, 1 skipped in 89.56s.
- Hygiene scan: no absolute paths, email addresses, or AGENTS rule-7 banned phrases in README.md, .gitignore, or NOTICE.
- `.gitignore` contains rules excluding raw DDInter CSV downloads and `work/b9_repro_20260930/`; `SOURCE.md` remains available.
- No code, model, or clinical CSV was edited. `.env` was not opened, read, or searched.
