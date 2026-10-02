# B19 Phase 4 — optional LLM work

The existing provider interface accepts system and prompt text and returns text. The Anthropic adapter implements it with messages.create. Groq now implements the same interface through the official OpenAI-compatible chat completions endpoint using Python's standard-library urllib. Request construction uses the configured model, system/user messages, temperature 0, a 400-token response cap and a 10-second timeout. Groq errors return fixed text; one retry is allowed for transient transport failures and HTTP 429 or 5xx. A process-level cap permits at most 80 attempts.

Official provider references checked for this task:

- Groq OpenAI compatibility: https://console.groq.com/docs/openai
- Groq API reference: https://console.groq.com/docs/api-reference

The dotenv loader is inside medsafe/llm/client.py. It reads only the package-root .env, only the three allowlisted names, and does not read MEDSAFE_LLM_ENABLED. Process environment takes precedence. A disabled dotenv switch was set for repository commands. Parser tests used temporary files with synthetic sentinel values; the real .env was not opened.

.env.example contains placeholders only. .gitignore excludes .env and .env.* while retaining .env.example. README.md documents optional setup. scripts/make_submission_zip.py builds an archive, excludes credential files, caches, virtual environments, work/ and the listed raw DDInter dumps, reopens it for an entry check, and prints its file inventory. Its ZIP behavior was exercised on a temporary fixture.

Offline suite: 317 passed, 1 skipped. Sixteen added tests cover dotenv allowlisting, comments, quotes, process precedence, the enable switch, oversized and malformed inputs, masked config, Groq request format, fixed errors, one 429 retry, deterministic fallback, a rejected extra sentence, archive exclusions, and UI routes/security checks. Existing assertions were not changed.

Live synthetic measurement ran through Groq. It covered 25 parser inputs and 15 summary cases. Parser: 0 accepted, 25 rejected. Summaries: 0 accepted, 15 rejected. Findings were byte-identical in 40 of 40 cases. The script printed key presence only and saved case-level results in reports/b19_llm_measurement.md and reports/b19_llm_measurement.json. No real prescription or patient data was used.

## Acceptance issue to resolve

The observed live run had no accepted summaries, so its byte-identity count is 40/40. The existing add_summaries path would store any accepted wording in Finding.explanation.plain_language. If a later run accepts a summary, serialized findings can differ even while rule IDs, severity, ordering and checker results stay fixed. Keeping the strict invariant when acceptance occurs needs a separate summary field outside findings; no response schema change was made in Run A.
