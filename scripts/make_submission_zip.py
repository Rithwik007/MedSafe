"""Build a submission archive while excluding credentials and raw source dumps."""
from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# The owner can add project-specific raw-data paths here.
EXCLUDE_PATHS = {
    "data/raw/ddinter/ddinter_downloads_code_*.csv",
    "work/",
}
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox",
}


def excluded(relative: str, output: Path) -> bool:
    path = Path(relative)
    if relative == "reports/b19_zip_listing.txt":
        return True
    if (ROOT / relative).resolve() == output.resolve():
        return True
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.parts and path.parts[0] == "work":
        return True
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return True
    if path.suffix == ".pyc" or path.name.endswith(".pyc"):
        return True
    if any(fnmatch.fnmatch(relative, pattern) for pattern in EXCLUDE_PATHS):
        return True
    if relative.startswith("data/raw/ddinter/") and path.name.startswith("ddinter_downloads_code_"):
        return True
    return False


def build(output: Path) -> tuple[list[tuple[str, int]], int]:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files: list[tuple[str, Path]] = []
    for candidate in ROOT.rglob("*"):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(ROOT).as_posix()
        if not excluded(relative, output):
            files.append((relative, candidate))
    files.sort(key=lambda item: item[0].casefold())

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, candidate in files:
            archive.write(candidate, relative)

    with zipfile.ZipFile(output, "r") as archive:
        names = archive.namelist()
        bad = [name for name in names if Path(name).name.startswith(".env")
               and Path(name).name != ".env.example"]
        if bad:
            output.unlink(missing_ok=True)
            raise RuntimeError("Archive credential-entry check failed.")
        entries = [(name, archive.getinfo(name).file_size) for name in names]
    return entries, output.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "reports" / "medsafe_submission.zip")
    args = parser.parse_args()
    entries, archive_bytes = build(args.output)
    print("Submission archive entries:")
    for name, size in entries:
        print(f"{name}\t{size}")
    print(f"Entry count: {len(entries)}")
    print(f"Uncompressed total: {sum(size for _, size in entries)} bytes")
    print(f"Archive size: {archive_bytes} bytes")
    print("Credential-entry check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
