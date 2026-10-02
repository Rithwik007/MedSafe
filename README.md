# MedSafe

Medication-safety decision-support research prototype. It demonstrates conservative prescription parsing, source-tracked rules, and an API. **Research prototype, not for clinical use.**

## What it does

The project parses a narrow set of prescription directions, normalizes documented drug names, and reports findings from local rules. A local model can add explicitly unverified estimates for some DDInter-listed pairs whose source severity is unspecified. Findings retain their source evidence, and unresolved input stays visible.

The rule engine loads 313 DDInter DDI rules for a whitelist of 30 drugs. These are a subset of the entire DDInter dataset. Some source severities are unspecified; their findings require pharmacist review. Mechanisms and recommendations remain empty when the source dataset does not provide them.

## Data sources and attribution

DDI rules derive from DDInter, Computational Biology & Drug Design Group ([download](https://ddinter.scbdd.com/download/), [terms](https://ddinter.scbdd.com/terms/)). The source dataset is licensed CC BY-NC-SA 4.0. Review the source terms before redistribution or commercial use. See [NOTICE](NOTICE), [data/raw/ddinter/SOURCE.md](data/raw/ddinter/SOURCE.md), and [reports/ddinter_import.md](reports/ddinter_import.md). The derived DDI rule CSV also identifies DDInter and its license in each row.

Drug-class lookup uses the NLM RxClass API. NLM attribution: “This product uses publicly available data from the U.S. National Library of Medicine (NLM), National Institutes of Health, Department of Health and Human Services; NLM is not responsible for the product and does not endorse or recommend this or any other product.”

Allergy, drug-disease and dose rows cite DailyMed labels in their source fields. The one dose row is a source-text check of an adult atorvastatin tablet limit; dose coverage remains narrow and does not incorporate lower co-medication-specific caps.

### Reproducing the DDInter import (optional)

Download the eight `ddinter_downloads_code_*.csv` files from the [DDInter download page](https://ddinter.scbdd.com/download/) and place them in `data/raw/ddinter/`. Read DDInter [terms](https://ddinter.scbdd.com/terms/) first: the source data is CC BY-NC-SA 4.0 and is limited to non-commercial use under those terms. Raw downloads are excluded from this repository; obtain them directly from DDInter. To rebuild the filtered rules without replacing the checked-in rules, use a separate output path, for example `python scripts/import_ddinter.py --output reports/ddinter_reimport/rules.csv`.

## Install

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,ml]"
```

## Run tests

```powershell
python -m pytest -q
```

Current recorded result: 329 passed, 1 skipped. The skipped test is the opt-in live LLM test.

## Run the synthetic demo

```powershell
python -B scripts/run_demo.py
```

The script runs three synthetic prescriptions with the local ML model enabled and LLM disabled. It writes text and JSON reports under `reports/demo/` and checks repeatability, allowing only the generated timestamp to differ.

## API usage

Start the API from the project directory:

```powershell
python -m uvicorn medsafe.api.app:app --reload
```

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/analyze-text?use_llm=false" \
  -H "Content-Type: application/json" \
  -d '{"patient":{"allergies":["amoxicillin"],"diagnoses":["myasthenia gravis"]},"prescription_text":"Amoxicillin\nCiprofloxacin"}'
```

Example with PowerShell:

```powershell
$body = @{ patient = @{ allergies = @("amoxicillin"); diagnoses = @("myasthenia gravis") }; prescription_text = "Amoxicillin`nCiprofloxacin" } | ConvertTo-Json -Depth 8
Invoke-RestMethod -Uri "http://127.0.0.1:8000/analyze-text?use_llm=false" -Method Post -ContentType "application/json" -Body $body
```

## Architecture and data workflow

The API receives structured or free-text input. The parser turns supported text into orders and keeps unresolved text in the report. The normalizer uses documented aliases; exact verified mappings resolve automatically. Fuzzy scores from 95 upward auto-accept, scores from 90 to below 95 return a suggestion for confirmation, and lower scores stay unresolved. Product-family names with ambiguous variants stay unresolved. Combination aliases preserve their documented ingredients, and unsupported multi-ingredient analysis stays unresolved.

The graph loader reads classes from `data/seed/drug_classes.csv`, while class rules load from `data/seed/class_rules.csv`. Some drug-class identifiers remain marked for verification; no class is guessed. Graph class matching is infrastructure only; no clinical class rule is populated.

Enter source-backed rows in `data/seed/` using the schemas in `data/seed/README_checker_csvs.md`. Leave a row out when its source or interpretation is uncertain. Run `python scripts/validate_checker_csvs.py`, then `python -m pytest -q`. Files under `data/review/` are worksheets and are not loaded by checkers.

## Limitations

- ML estimates are experimental and unverified. Major estimates are withheld; the user-facing message reports only a class-free withheld count.
- Dose checker status: PARTIAL (1 reviewed row; adult single-order checks only; not clinical review.)
- Disease matching uses exact phrases; allergy matching uses exact normalized ingredients.
- Allergy, drug-disease and dose rows come from drug labels and have source text checks recorded; this is not clinical review. The dose row has narrow coverage and does not apply lower co-medication-specific caps.
- The B12 spot check covered 25 unique pairs; it is small and does not establish model performance. The frozen rule suppresses Major ML notes because 0 of 9 sampled Major pairs had a definite answer.
- Live Groq measurement used 25 synthetic parser lines and 15 synthetic summary cases; no output passed the current guards. The observed findings stayed byte-identical in all 40 cases. This does not establish how the LLM behaves on other inputs.
- No warning does not establish that a prescription has no concern. The project has no PHI storage, authentication, audit service, FHIR integration, or clinical validation.

## LLM use and privacy

Optional LLM features are off by default. The Groq provider uses the standard library and needs no added dependency. Copy `.env.example` to `.env`, set `GROQ_API_KEY` and `MEDSAFE_LLM_MODEL` there, and set `MEDSAFE_LLM_PROVIDER=groq`. Choose a model ID from the Groq console. For an explicit synthetic run, set `MEDSAFE_LLM_ENABLED=1` in the terminal and send `use_llm=true` on the request. The enable flag is never read from `.env`. The existing Anthropic provider remains optional and requires `ANTHROPIC_API_KEY` in the process environment, a model ID and the optional `anthropic` package. A real `.env` file is git-ignored and must not be committed.

Parser fallback sends only an individual prescription line when deterministic parsing leaves it unparsed or LOW confidence. Do not submit real patient data. A strict JSON schema and source-substring, exact-normalizer, unit, and frequency guards reject unsupported extraction; rejected output leaves deterministic parsing in place.

The optional plain-language feature sends structured finding fields only. It does not send original prescription text or patient identifiers. Guards reject output that adds information or changes severity. Findings, order, and checker counts come from deterministic rules. Demos and tests use synthetic data and fake clients; tests make no network calls. Provider prompts are transmitted when the feature is enabled.

**Research prototype, not for clinical use.**
