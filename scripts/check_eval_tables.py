from pathlib import Path
import re

path = Path(__file__).resolve().parents[1] / "reports/ml_eval.md"
lines = path.read_text(encoding="utf-8").splitlines()
tables = []
i = 0
while i < len(lines) - 1:
    if lines[i].lstrip().startswith("|") and re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*", lines[i + 1]):
        header = lines[i]
        separator = lines[i + 1]
        count = lambda s: len([x for x in s.strip().strip("|").split("|")])
        expected, actual = count(header), count(separator)
        table = len(tables) + 1
        ok = expected == actual
        tables.append(ok)
        print(f"table {table}: {'PASS' if ok else 'FAIL'} (header={expected}, separator={actual})")
    i += 1
if not tables:
    print("FAIL: no markdown tables found")
    raise SystemExit(1)
print(f"Summary: {sum(tables)}/{len(tables)} tables valid")
raise SystemExit(0 if all(tables) else 1)
