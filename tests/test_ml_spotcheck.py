from scripts.export_ml_spotcheck import select_balanced_pairs

def test_per_drug_cap_counts_each_pair_against_both_drugs():
    buckets = {"Major":[("a","b"),("a","c"),("d","e")],
               "Moderate":[("a","d"),("e","f")], "Minor":[("b","f")]}
    selected, counts, shortfalls = select_balanced_pairs(
        buckets, {"Major":2,"Moderate":2,"Minor":1}, per_drug_cap=2, seed=21)
    assert all(value <= 2 for value in counts.values())
    assert not shortfalls
    for pair, _ in selected:
        assert counts[pair[0].casefold()] >= 1
        assert counts[pair[1].casefold()] >= 1

def test_class_quotas_met_when_feasible_and_shortfall_reported_otherwise():
    feasible = {"Major":[("a","b")], "Moderate":[("c","d")], "Minor":[("e","f")]}
    selected, _, shortfalls = select_balanced_pairs(feasible,
        {"Major":1,"Moderate":1,"Minor":1}, per_drug_cap=2, seed=7)
    assert len(selected) == 3 and not shortfalls
    impossible = {"Major":[("a","b"),("a","c")], "Moderate":[], "Minor":[]}
    selected, _, shortfalls = select_balanced_pairs(impossible,
        {"Major":2,"Moderate":1,"Minor":1}, per_drug_cap=1, seed=7)
    assert shortfalls == {"Major":1,"Moderate":1,"Minor":1}

def test_selection_deterministic_for_same_seed():
    buckets = {"Major":[("a","b"),("c","d"),("e","f")],
               "Moderate":[("g","h"),("i","j")], "Minor":[("k","l")]}
    args = (buckets, {"Major":2,"Moderate":1,"Minor":1})
    assert select_balanced_pairs(*args, seed=99) == select_balanced_pairs(*args, seed=99)

