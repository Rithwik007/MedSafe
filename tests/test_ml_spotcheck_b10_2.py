from pathlib import Path
import csv
from scripts.export_ml_spotcheck_b10_2 import (
    BINS, Candidate, probability_bin, stratified_select, write_sheet
)

def c(a,b,label,bin_):
    return Candidate((a,b),label,0.95,bin_)

def test_probability_bin_boundaries():
    assert probability_bin(0.705426,0.705426)==BINS[0]
    assert probability_bin(0.80,0.705426)==BINS[1]
    assert probability_bin(0.90,0.705426)==BINS[2]
    assert probability_bin(1.0,0.705426)==BINS[2]

def test_drug_cap_and_kcl_major_limit_hold():
    candidates=[
      c("potassium chloride","a","Major",BINS[0]),
      c("potassium chloride","b","Major",BINS[1]),
      c("c","d","Major",BINS[2]),
      c("a","e","Moderate",BINS[0]),
      c("f","g","Moderate",BINS[1]),
      c("h","i","Minor",BINS[2]),
    ]
    selected,counts,allocations,bincounts,shortfalls=stratified_select(
        candidates,{"Major":3,"Moderate":2,"Minor":1},cap=2,seed=20260930,kcl_major_cap=1)
    assert all(n<=2 for n in counts.values())
    assert sum(x.label=="Major" and "potassium chloride" in x.pair for x in selected)<=1
    assert len([x for x in selected if x.label=="Major"])==2
    assert shortfalls.get(("Major","TOTAL"))==1

def test_sampler_determinism_same_seed_and_quota_or_shortfall():
    candidates=[c(f"drug{i}",f"partner{i}","Major",BINS[i%3]) for i in range(18)]
    candidates += [c(f"mod{i}",f"m{i}","Moderate",BINS[i%3]) for i in range(18)]
    candidates += [c(f"min{i}",f"n{i}","Minor",BINS[i%3]) for i in range(18)]
    args=(candidates,{"Major":8,"Moderate":8,"Minor":8})
    one=stratified_select(*args,seed=7)
    two=stratified_select(*args,seed=7)
    assert one==two
    assert len([x for x in one[0] if x.label=="Major"])==8
    assert len([x for x in one[0] if x.label=="Moderate"])==8
    assert len([x for x in one[0] if x.label=="Minor"])==8
    assert not one[4]

def test_csv_review_fields_blank(tmp_path: Path):
    path=tmp_path/"sheet.csv"
    row=c("alpha","beta","Major",BINS[0])
    write_sheet(path,[row],seed=123)
    with path.open(newline="",encoding="utf-8") as f:
        record=next(csv.DictReader(f))
    assert record["probability_bin"]==BINS[0]
    assert record["sampling_seed"]=="123"
    assert all(record[key]=="" for key in ("source_checked","source_url","source_result","agrees","notes"))

