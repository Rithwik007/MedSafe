import csv
import shutil
from pathlib import Path

import pytest

from medsafe.core.normalizer import NormalizedDrug
from scripts import validate_checker_csvs as validator

FIXTURE = Path(__file__).parent / "fixtures" / "checker_csvs"
ERROR_FIXTURE = Path(__file__).parent / "fixtures" / "validator_three_errors"


def _seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    seed = tmp_path / "data" / "seed"
    seed.mkdir(parents=True)
    for path in FIXTURE.iterdir():
        shutil.copy(path, seed / path.name)

    def fake_normalize(name: str):
        if name == "TEST_DRUG":
            return NormalizedDrug("TEST_INGREDIENT", 100, "matched", ("TEST_INGREDIENT",))
        if name == "TEST_COMBO":
            return NormalizedDrug(None, 100, "matched", ("TEST_A", "TEST_B"))
        return NormalizedDrug(None, 0, "unresolved")

    monkeypatch.setattr(validator, "normalize_drug", fake_normalize)
    return seed


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_fixture_rows_pass_and_header_only_files_pass(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    issues, counts = validator.validate(seed)
    assert issues == []
    assert counts == {"allergy_rules.csv": 1, "drug_disease_rules.csv": 1, "dose_limits.csv": 1}
    for filename, columns in validator.SCHEMAS.items():
        _write(seed / filename, list(columns), [])
    issues, counts = validator.validate(seed)
    assert issues == []
    assert set(counts.values()) == {0}


def test_required_and_unknown_columns_are_reported(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    columns.remove("source_section")
    columns.append("unexpected")
    changed = {key: value for key, value in rows[0].items() if key in columns}
    changed["unexpected"] = "TEST_EXTRA"
    _write(path, columns, [changed])
    issues, _ = validator.validate(seed)
    messages = {(issue.column, issue.message) for issue in issues}
    assert ("source_section", "required column is missing") in messages
    assert ("unexpected", "unknown column") in messages


def test_required_values_and_bad_source_url_are_reported(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    rows[0]["reason"] = ""
    rows[0]["source_url"] = "ftp://example.invalid/source"
    rows[0]["source_section"] = ""
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    found = {(issue.column, issue.message) for issue in issues}
    assert ("reason", "must not be blank") in found
    assert ("source_section", "must not be blank") in found
    assert ("source_url", "must start with http:// or https://") in found


def test_three_error_fixture_reports_exact_issues(monkeypatch):
    def fake_normalize(name: str):
        return NormalizedDrug("TEST_INGREDIENT", 100, "matched", ("TEST_INGREDIENT",))

    monkeypatch.setattr(validator, "normalize_drug", fake_normalize)
    issues, _ = validator.validate(ERROR_FIXTURE)
    found = {(issue.column, issue.message) for issue in issues}
    assert found == {
        ("reason", "must not be blank"),
        ("source_url", "must start with http:// or https://"),
        ("match_type", "must be DIRECT or CROSS_REACTIVITY"),
    }


def test_dates_must_be_iso_not_future_and_ordered(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    rows[0]["accessed_on"] = "not-a-date"
    rows[0]["verified_on"] = "2999-01-01"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    found = {(issue.column, issue.message) for issue in issues}
    assert ("accessed_on", "must be a valid ISO date") in found
    assert ("verified_on", "date must not be in the future") in found


def test_reviewed_date_must_not_precede_access_date(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    rows[0]["verified_on"] = "2019-12-31"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.message == "must be on or after accessed_on" for issue in issues)


def test_severity_policy_and_allergy_match_type_are_enforced(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    rows[0]["label_category"] = "TEST_UNKNOWN"
    rows[0]["match_type"] = "TEST_UNKNOWN"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    found = {(issue.column, issue.message) for issue in issues}
    assert ("label_category", "not present in severity_policy.csv") in found
    assert ("match_type", "must be DIRECT or CROSS_REACTIVITY") in found


def test_drug_must_be_exact_and_dose_requires_single_ingredient(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "dose_limits.csv"
    columns, rows = _rows(path)
    rows[0]["drug"] = "TEST_COMBO"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.column == "drug" and "single-ingredient" in issue.message for issue in issues)
    rows[0]["drug"] = "TEST_UNKNOWN"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.column == "drug" and "exact curated match" in issue.message for issue in issues)


def test_unknown_condition_is_warning_unless_strict(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "drug_disease_rules.csv"
    columns, rows = _rows(path)
    rows[0]["condition"] = "TEST_NOT_LISTED"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.warning and issue.column == "condition" for issue in issues)
    issues, _ = validator.validate(seed, strict=True)
    assert any(not issue.warning and issue.column == "condition" for issue in issues)


def test_dose_numeric_unit_population_and_age_rules(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "dose_limits.csv"
    columns, rows = _rows(path)
    rows[0].update(max_single_dose="two", max_daily_dose="1", dose_unit="ml",
                   population="CHILD", age_min_years="120", age_max_years="18")
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    found = {(issue.column, issue.message) for issue in issues}
    assert ("max_single_dose", "must be a positive number") in found
    assert ("max_daily_dose", "must be greater than or equal to max_single_dose") not in found
    assert ("dose_unit", "must be a MASS unit from units.csv") in found
    assert ("population", "must equal ADULT") in found
    assert ("age_min_years", "must be less than age_max_years") in found


def test_daily_dose_cannot_be_below_single_dose(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "dose_limits.csv"
    columns, rows = _rows(path)
    rows[0]["max_single_dose"] = "2"
    rows[0]["max_daily_dose"] = "1"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.column == "max_daily_dose" and "greater than or equal" in issue.message
               for issue in issues)


def test_d1_allows_blank_age_bounds_only_with_label_population_phrase(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "dose_limits.csv"
    columns, rows = _rows(path)
    rows[0].update(population="adults (age range not stated by label)",
                   age_min_years="", age_max_years="")
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert issues == []


def test_d1_rejects_blank_ages_without_label_population_phrase(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "dose_limits.csv"
    columns, rows = _rows(path)
    rows[0].update(population="ADULT", age_min_years="", age_max_years="")
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.column == "age_min_years" and "age bounds must be numeric" in issue.message
               for issue in issues)


def test_d1_requires_both_age_cells_blank_when_label_gives_no_range(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "dose_limits.csv"
    columns, rows = _rows(path)
    rows[0].update(population="adults (age range not stated by label)",
                   age_min_years="18", age_max_years="")
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any(issue.column == "age_min_years" and "must be blank" in issue.message
               for issue in issues)


def test_duplicate_rule_ids_and_subject_keys_are_reported(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    rows.append(dict(rows[0]))
    rows[1]["reason"] = "TEST_SECOND_REASON"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    messages = [issue.message for issue in issues]
    assert "duplicate rule_id" in messages
    assert "duplicate drug/allergen, drug/condition, or drug/population key" in messages


def test_condition_synonyms_share_duplicate_key(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "drug_disease_rules.csv"
    columns, rows = _rows(path)
    rows[0]["condition"] = "TEST_CONDITION_ALIAS"
    rows.append(dict(rows[0]))
    rows[1]["rule_id"] = "TEST_RULE_2"
    rows[1]["condition"] = "TEST_CONDITION"
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any("duplicate drug/allergen, drug/condition" in issue.message for issue in issues)


def test_reviewer_and_verified_date_must_be_paired(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    path = seed / "allergy_rules.csv"
    columns, rows = _rows(path)
    rows[0]["verified_on"] = ""
    _write(path, columns, rows)
    issues, _ = validator.validate(seed)
    assert any("must both be blank or both be set" in issue.message for issue in issues)


def test_example_only_is_rejected_from_seed_data(tmp_path, monkeypatch):
    seed = _seed(tmp_path, monkeypatch)
    (seed / "bad.csv").write_text("TEST_COLUMN\nEXAMPLE_ONLY\n", encoding="utf-8")
    issues, _ = validator.validate(seed)
    assert any("EXAMPLE_ONLY is forbidden" in issue.message for issue in issues)
