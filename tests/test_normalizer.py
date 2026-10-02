import csv
from pathlib import Path

import pytest

from medsafe.core.normalizer import normalize_drug

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", [
    row.strip() for row in (ROOT / "data/seed/drug_whitelist.csv").read_text(encoding="utf-8-sig").splitlines()
    if row.strip() and not row.strip().startswith("#")
])
def test_every_whitelisted_drug_resolves(name):
    result = normalize_drug(name)
    assert result.status == "matched"
    assert result.ingredients


@pytest.mark.parametrize(("brand", "ingredients"), [
    ("Crocin 650", ("paracetamol",)),
    ("Crocin 650 mg", ("paracetamol",)),
    ("Crocin Pain Relief", ("caffeine", "paracetamol")),
    ("Dolo 650", ("paracetamol",)),
    ("Dolo Xtraa", ("caffeine", "paracetamol")),
    ("Augmentin", ("amoxicillin", "clavulanic acid")),
    ("Augmentin 625", ("amoxicillin", "clavulanic acid")),
    ("Glycomet", ("metformin",)),
    ("Glycomet 500 mg", ("metformin",)),
    ("Brufen 200", ("ibuprofen",)),
    ("Brufen 200mg", ("ibuprofen",)),
    ("Brufen 400", ("ibuprofen",)),
    ("Brufen 600", ("ibuprofen",)),
    ("Brufen P", ("ibuprofen", "paracetamol")),
    ("Combiflam", ("ibuprofen", "paracetamol")),
])
def test_verified_brand_maps_to_documented_ingredients(brand, ingredients):
    result = normalize_drug(brand)
    assert result.status == "matched"
    assert result.ingredients == ingredients


def test_fuzzy_score_at_least_95_auto_accepts():
    result = normalize_drug("atorvastati")
    assert result.status == "matched"
    assert result.confidence >= 95
    assert result.canonical == "Atorvastatin"


def test_paracetamol_brand_ingredient_uses_ddinter_synonym_for_matching():
    result = normalize_drug("Crocin 650")
    assert result.ingredients == ("paracetamol",)
    assert result.canonical == "Acetaminophen"


def test_strength_brands_are_verified_at_product_level():
    assert normalize_drug("Dolo 650").canonical == "Acetaminophen"
    assert normalize_drug("Crocin Advance 500mg").canonical == "Acetaminophen"
    # 1mg lists Crocin Advance 500mg, not generic shorthand Crocin 500mg.
    assert normalize_drug("Crocin 500mg").canonical is None


def test_strength_bearing_brand_product_is_source_bounded():
    assert normalize_drug("Dolo 650").canonical == "Acetaminophen"
    assert normalize_drug("Crocin Advance 500mg").canonical == "Acetaminophen"
    # Source identifies Crocin Advance 500mg, not unspecified Crocin 500mg.
    assert normalize_drug("Crocin 500mg").canonical is None


@pytest.mark.parametrize("typo", ["atorvastatim", "ibuprofenx", "methformin", "warfarin1", "atorvastat"])
def test_fuzzy_score_90_to_below_95_requires_confirmation(typo):
    result = normalize_drug(typo)
    assert 90 <= result.confidence < 95
    assert result.status == "suggested"
    assert result.canonical is None
    assert result.suggestion
    assert result.ingredients


@pytest.mark.parametrize("name", ["xyzxyzxyz", "hydroxyzine", "hydralazine", "clotrimazole", "metformim"])
def test_false_matches_remain_unresolved(name):
    result = normalize_drug(name)
    assert result.status == "unresolved"
    assert result.canonical is None
    assert not result.ingredients


@pytest.mark.parametrize("ambiguous_brand", ["Crocin", "Dolo", "Brufen"])
def test_ambiguous_brand_family_does_not_auto_map(ambiguous_brand):
    assert normalize_drug(ambiguous_brand).status == "unresolved"


def test_brand_rows_have_sources_and_verified_column():
    with (ROOT / "data/seed/synonyms.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {"source", "verified", "alias", "ingredients"} <= set(rows[0])
    assert all(row["source"] for row in rows)
    assert all(row["verified"] in {"yes", "no"} for row in rows)
