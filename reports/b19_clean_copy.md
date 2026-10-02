# B19 clean-copy verification

- Copy followed `.gitignore` exclusions and excluded the real `.env`; raw DDInter dumps were also omitted. `work/b9_repro_20260930/` was excluded.
- `python -m pytest -q`: 329 passed, 1 skipped.
- `python -B scripts/run_demo.py`: passed; each demo repeated across three runs except `generated_at`.
- Local server: GET `/health` returned 200 with 313 clinical rules loaded; GET `/` returned 200; synthetic POST `/analyze-text?use_llm=false` returned 200.
- This run used the final source wording. Live LLM was disabled.
