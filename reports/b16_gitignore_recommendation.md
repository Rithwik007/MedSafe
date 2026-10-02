# B16 `.gitignore` recommendation

Existing root `.gitignore` was not edited because B16 says to leave existing files untouched. It already ignores `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.py[cod]`, and `.env/`.

Suggested additions for the owner to review:

```gitignore
venv/
env/
.cache/
.ruff_cache/
*.log
```

Keep `.env.example` tracked; keep real `.env` ignored.

## On-disk sizes

| Folder | Files | Bytes | MiB |
|---|---:|---:|---:|
| `models/` | 3 | 7,515,007 | 7.17 |
| `data/` | 31 | 13,259,656 | 12.65 |
| `data/raw/ddinter/` | 9 | 13,135,540 | 12.53 |

Raw DDInter CSV downloads are the main licensing concern. `data/raw/ddinter/SOURCE.md` records the DDInter source and terms. Recommend leaving the eight raw CSV downloads out of a public submission until the owner checks whether the licence allows that distribution. Keep an attribution/source note if the data is redistributed under permitted terms. The model folder is 7.17 MiB; it is local and checksum-verified at runtime, so size alone does not require excluding it.
