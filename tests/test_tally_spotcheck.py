import csv

from scripts.tally_spotcheck import CATEGORIES, CAVEAT, render_tally, tally_csv


def _write_sheet(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["pair", "predicted_label", "agrees"])
        writer.writeheader()
        writer.writerows(rows)


def test_tally_counts_all_values_blank_and_invalid_by_label(tmp_path):
    sheet = tmp_path / "review.csv"
    _write_sheet(sheet, [
        {"pair": "A + B", "predicted_label": "Major", "agrees": "agree"},
        {"pair": "C + D", "predicted_label": "Major", "agrees": "disagree"},
        {"pair": "E + F", "predicted_label": "Minor", "agrees": "unclear"},
        {"pair": "G + H", "predicted_label": "Minor", "agrees": ""},
        {"pair": "I + J", "predicted_label": "Minor", "agrees": "aggre"},
    ])
    result = tally_csv(sheet)
    assert result["row_count"] == 5
    assert {key: len(value) for key, value in result["overall"].items()} == {
        "agree": 1, "disagree": 1, "unclear": 1, "unfilled": 1, "invalid": 1}
    assert result["by_predicted_label"]["Major"]["agree"] == [("A + B", None)]
    assert result["by_predicted_label"]["Minor"]["unfilled"] == [("G + H", None)]
    assert result["by_predicted_label"]["Minor"]["invalid"] == [("I + J", "aggre")]
    assert set(result["overall"]) == set(CATEGORIES)


def test_blank_agrees_is_unfilled_not_unclear(tmp_path):
    sheet = tmp_path / "blank.csv"
    _write_sheet(sheet, [{"pair": "A + B", "predicted_label": "Major", "agrees": " "}])
    result = tally_csv(sheet)
    assert len(result["overall"]["unfilled"]) == 1
    assert result["overall"]["unclear"] == []


def test_empty_file_returns_zero_counts(tmp_path):
    sheet = tmp_path / "empty.csv"
    sheet.write_text("", encoding="utf-8")
    result = tally_csv(sheet)
    assert result["row_count"] == 0
    assert all(result["overall"][category] == [] for category in CATEGORIES)
    assert result["by_predicted_label"] == {}


def test_tally_output_lists_pairs_and_fixed_caveat(tmp_path):
    sheet = tmp_path / "review.csv"
    _write_sheet(sheet, [{"pair": "A + B", "predicted_label": "Major", "agrees": "unclear"}])
    text = render_tally(tally_csv(sheet))
    assert "unclear: 1" in text
    assert "- A + B" in text
    assert CAVEAT in text
