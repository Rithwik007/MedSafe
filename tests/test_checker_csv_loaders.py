import csv

from medsafe.checkers import stubs


def test_checker_loaders_ignore_data_review(tmp_path, monkeypatch):
    seed = tmp_path / "data" / "seed"
    review = tmp_path / "data" / "review"
    seed.mkdir(parents=True)
    review.mkdir(parents=True)
    for filename, columns in stubs.CHECKER_COLUMNS.items():
        with (seed / filename).open("w", newline="", encoding="utf-8") as stream:
            csv.writer(stream).writerow(columns)
    with (review / "checker_rows_template.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(stubs.CHECKER_COLUMNS["allergy_rules.csv"])
        writer.writerow(["EXAMPLE_ONLY"] * len(stubs.CHECKER_COLUMNS["allergy_rules.csv"]))
    monkeypatch.setattr(stubs, "ROOT", tmp_path)
    assert stubs.stub_status("allergy_rules.csv")[0] == "NOT_RUN_NO_DATA"

