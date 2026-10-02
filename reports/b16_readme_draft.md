# MedSafe

Medication-safety decision-support research prototype. It demonstrates prescription parsing, source-tracked rules, and an API. **Research prototype, not for clinical use.**

## What it does

The project parses a narrow set of prescription directions, normalizes verified drug names, and reports findings from local rules. It also adds explicitly unverified machine-learning notes for some DDI pairs whose source severity is unspecified. Findings retain their source evidence and unresolved input stays visible.

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

Current recorded result: 301 passed, 1 skipped. The skipped test is the opt-in live LLM test; B16 did not run it.

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

## Data sources

DDI rules derive from DDInter and are stored under `data/seed/`; raw source downloads and source notes are under `data/raw/ddinter/`. Allergy and drug-disease rows cite DailyMed labels in their CSV source fields. Project owner must check source licence terms before any commercial use.

## Architecture

The API receives structured or free-text input. The parser turns supported text into orders and keeps unresolved text in the report. The normalizer maps only documented drug aliases. Deterministic checkers compare orders with local DDI, duplicate, allergy, and disease rules. The report shows source details and unresolved inputs. A local model can add an unverified note without changing a rule finding. The optional LLM layer is off by default and can only assist parsing or wording behind guards.

## Limitations

- ML estimates are unverified; Major estimates are withheld.
- Dose checks are not built; the dose checker reports `NOT_RUN_NO_DATA`.
- Clinical rows are source-text-verified, not clinical review.
- Disease matching uses exact phrases only.
- Allergy matching uses exact normalized ingredients only.
- Rule coverage is limited. No warning does not establish that a prescription has no concern.
- The B12 spot-check tally is small and its recorded category total does not match the 25 rows in the blind CSV.
- Live LLM acceptance rate is unknown; the B16 test used no provider calls.

**Research prototype, not for clinical use.**

## B16 handling note

This is a proposed README replacement. B16 also says to leave existing files untouched. The existing root README was therefore not edited. It contains outdated feature statements and a local checkout path; reconcile those before submission under a task that permits README edits.
