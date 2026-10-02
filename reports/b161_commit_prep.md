# B16.1 Part D: commit preparation (read-only)

## Repository sizes

- `models/`: 7,515,007 bytes (3 files).
- `data/`: 13,259,656 bytes (31 files).
- `data/raw/ddinter/`: 13,135,540 bytes total (eight original CSV dumps plus source note). Individual CSV sizes: A 3,343,434; B 867,726; D 1,520,704; H 705,088; L 3,885,702; P 317,460; R 1,793,766; V 700,777 bytes.
- Files over 5 MB found: `models/drug_index.json` (6,871,078 bytes) and `work/b9_repro_20260930/models/drug_index.json` (6,871,078 bytes).
- No `.git/` directory exists. B16.1 did not initialize Git.

## Files needing a human decision before public push

| Files / contents | Decision | Recommendation | Reason |
|---|---|---|---|
| `data/raw/ddinter/ddinter_downloads_code_*.csv` (eight files) | Whether to redistribute the original DDInter dumps publicly | Hold them out until the owner confirms redistribution terms; if included, retain required attribution and CC BY-NC-SA 4.0 terms | `data/raw/ddinter/SOURCE.md` says the source license is CC BY-NC-SA 4.0 and use is noncommercial; public redistribution and derivative obligations need owner review. |
| `work/b9_repro_20260930/` | Whether this reproduction archive belongs in the submission | Exclude from a polished public submission if it is not needed to reproduce a reported result; it duplicates a 6.87 MB model index and adds size | It is an auxiliary historical reproduction tree, not the primary runtime model directory. Confirm no required evidence depends on it before excluding. |
| `reports/b14_final_report.md`, `reports/b14_staging/*.csv`, `reports/b14_staging/review_note.txt` | Whether to publish the intentional reviewer name `Rithwik` | Keep if the owner wants provenance visible; remove consistently only if choosing an anonymous repository | These are reviewer provenance fields. The pasted B16 verdict says this is the owner's choice and recommends keeping it for a hackathon repo. This scan for Part B was limited to README/.gitignore, not these reports. |
| `models/` | Whether model artifacts should ship | Keep the primary model artifacts if local ML demo capability is part of the submission | Runtime loads these local checksum-verified files; directory is 7.17 MiB. |

No names/emails or API keys were added to README or `.gitignore`. `.env.example` contains placeholders, but it should still be checked in the staged-file review.

## Commands to run later (printed only; none were executed)

Substitute the repository URL and intended branch before running push commands. Review staged files before committing, and do not stage raw DDInter dumps until the licensing decision above is settled.

```powershell
git init
git status --short
git add .
git status --short
git diff --cached --stat
Get-ChildItem -Recurse -File -Force | Where-Object { $_.FullName -notmatch '\.git\|__pycache__' } | Select-String -Pattern '(?i)(sk-ant-api03-[A-Za-z0-9_-]{20,}|ANTHROPIC_API_KEY\s*=\s*["'']?[^"''\s<][^"''\s]*)' | Select-Object Path,LineNumber
# After reviewing the staged-file list, diff, key-scan result, and licensing decision:
git commit -m "Prepare MedSafe submission"
git branch -M main
git remote add origin <OWNER_REPOSITORY_URL>
git push -u origin main
```

Do not push if the key scan reports a match. The `git add .` command is included because requested, but it stages all non-ignored files; review the status before proceeding and unstage anything that should not be public. Rotate any development API key before a public release.
