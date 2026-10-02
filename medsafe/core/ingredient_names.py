"""Canonical ingredient display names from the seed CSV."""
import csv
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "data/seed/ingredient_names.csv"


def display_name(ingredient: str) -> str:
    with PATH.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["ingredient"].strip().casefold() == ingredient.strip().casefold():
                return row["display_name"].strip() or ingredient
    return ingredient
