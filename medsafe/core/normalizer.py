"""Exact and conservative fuzzy drug-name matching from curated local data."""
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
WHITELIST_PATH = ROOT / "data/seed/drug_whitelist.csv"
SYNONYMS_PATH = ROOT / "data/seed/synonyms.csv"

Status = Literal["matched", "suggested", "unresolved"]


@dataclass(frozen=True)
class NormalizedDrug:
    canonical: str | None
    confidence: float
    status: Status = "unresolved"
    ingredients: tuple[str, ...] = ()
    suggestion: str | None = None
    reason: str | None = None


def _clean(value: str, *, strip_strength: bool = False) -> str:
    value = value.casefold().strip()
    if strip_strength:
        value = re.sub(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _load_maps() -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], dict[str, str]]:
    exact: dict[str, tuple[str, ...]] = {}
    display: dict[str, str] = {}
    if WHITELIST_PATH.exists():
        for raw in WHITELIST_PATH.read_text(encoding="utf-8-sig").splitlines():
            name = raw.strip()
            if name and not name.startswith("#"):
                key = _clean(name)
                exact[key] = (name,)
                display[key] = name
    # Generic aliases are explicit known synonym relationships.
    for alias, ingredient in {
        "paracetamol": "paracetamol", "acetaminophen": "Acetaminophen",
    }.items():
        exact[_clean(alias)] = (ingredient,)
        display[_clean(alias)] = alias

    if SYNONYMS_PATH.exists():
        with SYNONYMS_PATH.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("verified", "").strip().casefold() not in {"yes", "true", "1"}:
                    continue
                alias = row.get("alias", "").strip()
                ingredients = tuple(x.strip() for x in row.get("ingredients", "").split("|") if x.strip())
                if alias and ingredients:
                    key = _clean(alias)
                    exact[key] = ingredients
                    display[key] = alias

    # Strength-bearing product names get a secondary exact key without strength.
    for key, ingredients in list(exact.items()):
        without_strength = _clean(key, strip_strength=True)
        if without_strength and without_strength not in exact:
            exact[without_strength] = ingredients
            display[without_strength] = display[key]
    return exact, {k: v for k, v in exact.items()}, display


_EXACT, _FUZZY, _DISPLAY = _load_maps()
CANONICAL_EQUIVALENTS = {"paracetamol": "Acetaminophen", "acetaminophen": "Acetaminophen"}


def normalize_drug(raw: str) -> NormalizedDrug:
    full_key = _clean(raw)
    product_key = _clean(re.sub(r"(?<=\d)\s*(?:mg|mcg|g|ml)\b", " ", raw, flags=re.I))
    stripped_key = _clean(raw, strip_strength=True)
    for key in (full_key, product_key, stripped_key):
        if key in _EXACT:
            ingredients = _EXACT[key]
            canonical = CANONICAL_EQUIVALENTS.get(ingredients[0].casefold(), ingredients[0]) if len(ingredients) == 1 else None
            return NormalizedDrug(canonical, 100.0, "matched", ingredients)
    if not full_key:
        return NormalizedDrug(None, 0.0, reason="No drug name provided.")

    choices = list(_FUZZY)
    match = process.extractOne(full_key, choices, scorer=fuzz.ratio, score_cutoff=90)
    if match is None:
        return NormalizedDrug(None, 0.0, reason="No curated drug name matched the input.")
    key, score, _ = match
    ingredients = _FUZZY[key]
    suggestion = _DISPLAY.get(key, key)
    if score >= 95:
        canonical = CANONICAL_EQUIVALENTS.get(ingredients[0].casefold(), ingredients[0]) if len(ingredients) == 1 else None
        return NormalizedDrug(canonical, float(score), "matched", ingredients,
            suggestion=suggestion, reason="Fuzzy match >=95; verify spelling in source text.")
    return NormalizedDrug(None, float(score), "suggested", ingredients,
        suggestion=suggestion, reason="Candidate needs user confirmation before analysis.")


CONDITION_ALIASES = {"kidney disease": "ckd", "chronic kidney disease": "ckd", "ckd": "ckd"}


def normalize_condition(raw: str) -> str | None:
    key = re.sub(r"\s+", " ", raw.lower().strip())
    return CONDITION_ALIASES.get(key)
