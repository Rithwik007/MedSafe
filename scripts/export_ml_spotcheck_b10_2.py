from __future__ import annotations
import csv
import json
import random
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from medsafe.ml.data import load_ddinter
from medsafe.ml.features import pair_features
from medsafe.ml.predict import load_model

SEED=20260930
TARGETS={"Major":8,"Moderate":8,"Minor":8}
REVIEW_FIELDS=("source_checked","source_url","source_result","agrees","notes")
BINS=("[tau, 0.80)","[0.80, 0.90)","[0.90, 1.00]")

@dataclass(frozen=True)
class Candidate:
    pair: tuple[str,str]
    label: str
    probability: float
    probability_bin: str

def probability_bin(probability: float,tau: float) -> str | None:
    if tau <= probability < 0.80: return BINS[0]
    if 0.80 <= probability < 0.90: return BINS[1]
    if 0.90 <= probability <= 1.00: return BINS[2]
    return None

def allocate_strata(counts: dict[str,int],quota:int) -> dict[str,int]:
    total=sum(counts.get(b,0) for b in BINS)
    target=min(quota,total)
    if total==0:return {b:0 for b in BINS}
    raw={b:target*counts.get(b,0)/total for b in BINS}
    allocation={b:min(counts.get(b,0),int(raw[b])) for b in BINS}
    remaining=target-sum(allocation.values())
    order=sorted(BINS,key=lambda b:(-(raw[b]-int(raw[b])),BINS.index(b)))
    for b in order:
        if remaining and allocation[b]<counts.get(b,0):
            allocation[b]+=1; remaining-=1
    return allocation

def stratified_select(candidates:list[Candidate],targets:dict[str,int]=TARGETS,
                      cap:int=2,seed:int=SEED,kcl_major_cap:int=1):
    rng=random.Random(seed)
    by_label={lab:{b:[] for b in BINS} for lab in targets}
    for c in candidates: by_label[c.label][c.probability_bin].append(c)
    selected=[]; drug_counts=Counter(); allocations={}; selected_bins=Counter(); shortfalls={}
    for label,target in targets.items():
        sizes={b:len(by_label[label][b]) for b in BINS}
        alloc=allocate_strata(sizes,target); allocations[label]=alloc
        chosen_label=[]
        for b in BINS:
            pool=sorted(by_label[label][b],key=lambda c:tuple(x.casefold() for x in c.pair))
            rng.shuffle(pool)
            got=0
            for c in pool:
                if got>=alloc[b]:break
                if any(drug_counts[d.casefold()]>=cap for d in c.pair):continue
                if label=="Major" and any(d.casefold()=="potassium chloride" for d in c.pair):
                    used=sum(x.label=="Major" and any(d.casefold()=="potassium chloride" for d in x.pair) for x in selected + chosen_label)
                    if used>=kcl_major_cap:continue
                chosen_label.append(c); got+=1
                for d in c.pair: drug_counts[d.casefold()]+=1
            selected_bins[(label,b)]+=got
            if got<alloc[b]:shortfalls[(label,b)]=alloc[b]-got
        selected.extend(chosen_label)
        if len(chosen_label)<target:
            shortfalls[(label,"TOTAL")]=target-len(chosen_label)
    return selected,dict(drug_counts),allocations,dict(selected_bins),shortfalls

def make_pool(model,unknown,whitelist:set[str]) -> tuple[list[Candidate],dict[str,int]]:
    all_counts=Counter(); candidates=[]
    rows=list(unknown.itertuples(index=False))
    eligible=[]; rowmeta=[]
    for row in rows:
        a,b=row.drug_a.casefold(),row.drug_b.casefold()
        if a not in model.vectors.vectors or b not in model.vectors.vectors:continue
        pair=tuple(sorted((a,b)))
        if pair not in model.listed_pairs or pair not in model.unlabeled_pairs:continue
        eligible.append(pair_features(a,b,model.vectors)); rowmeta.append((a,b))
    if eligible:
        probs=model.classifier.predict_proba(np.vstack(eligible))
        classes=model.classifier.classes_
        for (a,b),values in zip(rowmeta,probs):
            i=int(np.argmax(values)); score=float(values[i]); label=str(classes[i]).title()
            if score < model.tau:continue
            bname=probability_bin(score,model.tau)
            if bname and label in TARGETS:all_counts[(label,bname)]+=1
            if a not in whitelist or b not in whitelist:continue
            if bname and label in TARGETS:
                candidates.append(Candidate(tuple(sorted((a,b))),label,score,bname))
    return candidates,dict(all_counts)

def write_sheet(path:Path,rows:list[Candidate],seed:int=SEED):
    fields=["pair","predicted_label","probability_bin","sampling_seed",*REVIEW_FIELDS]
    with path.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for c in rows:
            writer.writerow({"pair":" + ".join(c.pair),"predicted_label":c.label,
                "probability_bin":c.probability_bin,"sampling_seed":seed,
                **{field:"" for field in REVIEW_FIELDS}})

def sample_kcl(rows:list[Candidate],selected:list[Candidate],seed:int=SEED,limit:int=5):
    selected_pairs={c.pair for c in selected}
    pool=[c for c in rows if c.label=="Major" and c.pair not in selected_pairs
          and any(d.casefold()=="potassium chloride" for d in c.pair)]
    rng=random.Random(seed+1); result=[]
    for b in BINS:
        bucket=[x for x in pool if x.probability_bin==b]
        bucket.sort(key=lambda x:tuple(y.casefold() for y in x.pair));rng.shuffle(bucket)
        result.extend(bucket)
    return result[:limit]

def main():
    model=load_model()
    if not model.enabled:raise SystemExit("Shipped model gate disabled.")
    audit=load_ddinter()
    whitelist={x.casefold() for x in audit.whitelist_present}
    candidates,all_counts=make_pool(model,audit.unlabeled_pairs,whitelist)
    selected,drug_counts,allocations,selected_bins,shortfalls=stratified_select(candidates)
    b10_1=ROOT/"reports/ml_spotcheck_b10_1.csv"
    current=ROOT/"reports/ml_spotcheck.csv"
    if current.exists() and not b10_1.exists():shutil.copy2(current,b10_1)
    write_sheet(current,selected)
    kcl=sample_kcl(candidates,selected)
    write_sheet(ROOT/"reports/ml_spotcheck_kcl.csv",kcl)
    pool=Counter((c.label,c.probability_bin) for c in candidates)
    print(f"Seed: {SEED}; shipped tau: {model.tau:.6f}")
    print("Pool by class and bin (all covered; after both-drugs-whitelist filter; selected after cap):")
    print("| Class | Probability bin | All covered | After both-drugs whitelist | After cap/selected |")
    print("|---|---|---:|---:|---:|")
    for label in TARGETS:
        for b in BINS:
            print(f"| {label} | {b} | {all_counts.get((label,b),0)} | {pool[(label,b)]} | {selected_bins.get((label,b),0)} |")
    print("All-covered class totals:",json.dumps({lab:sum(all_counts[(lab,b)] for b in BINS) for lab in TARGETS},sort_keys=True))
    for (label,b),n in shortfalls.items():print(f"SHORTFALL {label} {b}: {n}")
    print("Per-drug main-sheet row counts:",json.dumps(dict(sorted(drug_counts.items())),sort_keys=True))
    print(f"KCl Major appendix rows: {len(kcl)} (excluded from main Major sample; up to 5)")
    print(f"Main sheet: {current}; rows={len(selected)}")
    print(f"KCl appendix: {ROOT/'reports/ml_spotcheck_kcl.csv'}; rows={len(kcl)}")

if __name__=="__main__":main()
