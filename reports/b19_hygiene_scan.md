# B19 hygiene scan

Scope: README, docs, static UI, scripts and reports. The real `.env` was excluded.

- Project-configured key was present in process memory for the scan; zero files matched its value.
- API-key pattern scan: 0 matches. Email scan: 0 matches.
- Personal-name scan: 15 matches, all from the intentional B14 reviewer provenance.
- Absolute-path scan: 1 match in an older report patch; retained under the instruction not to edit earlier reports.
- Broad phone-like pattern: 76 files matched. This pattern also flags dates, identifiers, hashes and numeric data; these are potential matches, not confirmed phone numbers.
- Policy phrase scan: 23 files matched. Matches span retained historical reports, ML evidence and frozen utility scripts. Earlier report artifacts and frozen ML files were left untouched. The scan is therefore not clean.

No secret value or matching file path was written to this report.
