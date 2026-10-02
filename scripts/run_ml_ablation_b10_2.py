from __future__ import annotations
import hashlib, json, shutil, subprocess, sys, tempfile, textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.stats import spearmanr
from sklearn.model_selection import train_test_split
from medsafe.ml.config import SEED
from medsafe.ml.data import load_ddinter
from medsafe.ml.features import pair_matrix,pair_features
from medsafe.ml.predict import load_model
from medsafe.ml.training import _all_class_probabilities,metrics

def validation_partition(edges):
 train,held=train_test_split(edges,test_size=0.30,random_state=SEED,stratify=edges["severity"])
 validation,_reserved=train_test_split(held,test_size=0.50,random_state=SEED+1,stratify=held["severity"])
 return train.reset_index(drop=True),validation.reset_index(drop=True)

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()

def distribution(model,unknown,whitelist,train):
 rows=list(unknown.itertuples(index=False)); feats=[]; positions=[]
 for i,r in enumerate(rows):
  a,b=r.drug_a.casefold(),r.drug_b.casefold(); pair=tuple(sorted((a,b)))
  if a in model.vectors.vectors and b in model.vectors.vectors and pair in model.listed_pairs and pair in model.unlabeled_pairs:
   feats.append(pair_features(a,b,model.vectors));positions.append(i)
 labels=["Abstained"]*len(rows)
 if feats:
  prob=model.classifier.predict_proba(np.vstack(feats))
  for pos,p in zip(positions,prob):
   j=int(np.argmax(p))
   if p[j]>=model.tau:labels[pos]=str(model.classifier.classes_[j]).title()
 pairs=[(r.drug_a.casefold(),r.drug_b.casefold(),lab) for r,lab in zip(rows,labels)]
 major=[p for p in pairs if p[2]=="Major"]; shares=[];hist=[]
 for drug in sorted(whitelist):
  incident=[p for p in pairs if drug in p[:2]]
  if incident:
   hist_rows=train.loc[(train.drug_a.str.casefold()==drug)|(train.drug_b.str.casefold()==drug)]
   if len(hist_rows):
    shares.append(sum(p[2]=="Major" for p in incident)/len(incident))
    hist.append(float(hist_rows.severity.eq("Major").mean()))
 kcl=sum("potassium chloride" in p[:2] for p in major)
 return {"major_count":len(major),"major_share":len(major)/len(pairs),
  "kcl_major_count":kcl,"kcl_share_of_major":kcl/len(major) if major else 0,
  "abstained_share":sum(p[2]=="Abstained" for p in pairs)/len(pairs),
  "spearman_rho":float(spearmanr(shares,hist).statistic),
  "major_pairs":{tuple(sorted(p[:2])) for p in major}}

def run_temp(temp):
 repo=temp/"MedSafe"
 shutil.copytree(ROOT,repo,ignore=shutil.ignore_patterns(".pytest_cache","__pycache__",".venv","work"))
 child=r'''
import json
import numpy as np
from sklearn.model_selection import train_test_split
from scipy.stats import spearmanr
from medsafe.ml.config import SEED,SEVERITIES
from medsafe.ml.data import load_ddinter
from medsafe.ml.features import DrugVectors,fit_drug_vectors,pair_matrix
from medsafe.ml.training import make_classifier,_all_class_probabilities,choose_tau,metrics
def split(edges):
 train,held=train_test_split(edges,test_size=.30,random_state=SEED,stratify=edges.severity)
 val,_reserved=train_test_split(held,test_size=.50,random_state=SEED+1,stratify=held.severity)
 return train.reset_index(drop=True),val.reset_index(drop=True)
audit=load_ddinter(); train,val=split(audit.labeled_pairs)
vectors=fit_drug_vectors(train,seed=SEED)
cols=["degree","major_fraction","moderate_fraction","minor_fraction"]+[f"svd_{i}" for i in range(1,17)]
keep=[i for i,n in enumerate(cols) if n not in {"major_fraction","moderate_fraction","minor_fraction"}]
vectors=DrugVectors({d:v[keep] for d,v in vectors.vectors.items()},len(keep))
clf=make_classifier("hist_gradient_boosting",SEED)
clf.fit(pair_matrix(train,vectors),train.severity.to_numpy(dtype=object))
yv=val.severity.to_numpy(dtype=object); pv=_all_class_probabilities(clf,pair_matrix(val,vectors))
tau=choose_tau(yv,pv); vm=metrics(yv,pv,tau)
u=audit.unlabeled_pairs; pu=_all_class_probabilities(clf,pair_matrix(u,vectors))
mx=pu.argmax(axis=1); conf=pu.max(axis=1); pred=np.asarray(SEVERITIES,dtype=object)[mx]
pred=np.where(conf>=tau,pred,"Abstained")
white={d.casefold() for d in audit.whitelist_present}; major=np.flatnonzero(pred=="Major")
kcl=[i for i in major if "potassium chloride" in {u.iloc[i].drug_a.casefold(),u.iloc[i].drug_b.casefold()}]
sh=[]; hist=[]
for d in sorted(white):
 mask=((u.drug_a.str.casefold()==d)|(u.drug_b.str.casefold()==d)).to_numpy()
 tr=train.loc[(train.drug_a.str.casefold()==d)|(train.drug_b.str.casefold()==d)]
 if mask.any() and len(tr):
  sh.append(float(np.sum((pred=="Major")&mask)/mask.sum()));hist.append(float(tr.severity.eq("Major").mean()))
rho=float(spearmanr(sh,hist).statistic)
print(json.dumps({"validation":vm,"tau":tau,"unknown":{"total":len(u),"major_count":len(major),"major_share":len(major)/len(u),"kcl_major_count":len(kcl),"kcl_share_of_major":len(kcl)/len(major) if len(major) else 0,"abstained_share":float(np.mean(pred=="Abstained")),"spearman_rho":rho,"major_pairs":[sorted([u.iloc[i].drug_a,u.iloc[i].drug_b]) for i in major]}}))
'''
 runner=repo/"_b10_2_ablation_child.py";runner.write_text(textwrap.dedent(child),encoding="utf-8")
 proc=subprocess.run([sys.executable,str(runner)],cwd=repo,text=True,capture_output=True,check=True)
 return json.loads(proc.stdout.strip().splitlines()[-1])

def main():
 idx=json.loads((ROOT/"models/drug_index.json").read_text(encoding="utf-8"))
 manifest=json.loads((ROOT/"models/manifest.json").read_text(encoding="utf-8"))
 hashes={name:sha(ROOT/"models"/name) for name in manifest["files"]}
 audit=load_ddinter(); train,validation=validation_partition(audit.labeled_pairs)
 shipped=load_model(); y=validation.severity.to_numpy(dtype=object)
 sm=metrics(y,_all_class_probabilities(shipped.classifier,pair_matrix(validation,shipped.vectors)),shipped.tau)
 white={d.casefold() for d in audit.whitelist_present}
 su=distribution(shipped,audit.unlabeled_pairs,white,train)
 with tempfile.TemporaryDirectory(prefix="medsafe-b10-2-") as t: ab=run_temp(Path(t))
 au=ab["unknown"]; overlap=len(su["major_pairs"]&{tuple(sorted(x)) for x in au.pop("major_pairs")})
 lines=["# B10.2 own-label-feature ablation","",
 "Ablation ran in a temporary copy, deleted after completion. HistGradientBoosting model family, seed, and RANDOM_PAIR train/validation split match the shipped workflow. Only direct per-drug severity-fraction dimensions and their pairwise sum, absolute-difference, and product columns were removed. No test metric was computed.","",
 "drug_index.json vector_columns: "+", ".join(idx["vector_columns"])+".",
 "Removed direct per-drug label-history dimensions: major_fraction, moderate_fraction, minor_fraction, including their derived sum/difference/product columns. Degree and SVD retained. SVD embeds severity-weighted training adjacency and may retain indirect label-pattern information; this is not a full label-information ablation.","",
 "## RANDOM_PAIR validation metrics","",
 "| Model | Tau | Macro-F1 | Major P | Major R | Major F1 | Brier | Confusion matrix [Major, Moderate, Minor] |",
 "|---|---:|---:|---:|---:|---:|---:|---|"]
 def row(name,tau,m):
  q=m["per_class"]["Major"];cm="; ".join(",".join(map(str,r)) for r in m["confusion_matrix"])
  return f"| {name} | {tau:.6f} | {m['macro_f1']:.4f} | {q['precision']:.4f} | {q['recall']:.4f} | {q['f1']:.4f} | {m['brier_score']:.4f} | {cm} |"
 lines += [row("Shipped",shipped.tau,sm),row("Ablated",ab["tau"],ab["validation"]),"",
 "## Unknown-pair estimates (unlabeled; descriptive only)","",
 "| Model | Major count | Major share of all Unknown | KCl Major count | KCl share of Major estimates | Abstained share | Spearman rho (whitelist predicted vs training Major share) |",
 "|---|---:|---:|---:|---:|---:|---:|"]
 def ur(name,x):return f"| {name} | {x['major_count']} | {x['major_share']:.4f} | {x['kcl_major_count']} | {x['kcl_share_of_major']:.4f} | {x['abstained_share']:.4f} | {x['spearman_rho']:.4f} |"
 lines += [ur("Shipped",su),ur("Ablated",au),"",f"Major-estimate pair overlap: {overlap}.","",
 f"Validation macro-F1 change, ablated minus shipped: {ab['validation']['macro_f1']-sm['macro_f1']:+.4f}.",
 "Measurements only; ablation does not establish cause and does not validate predictions on unlabeled pairs.","",
 "## Shipped model checksum verification",""]
 for name,actual in hashes.items():
  expected=manifest["files"][name]["sha256"]
  lines.append(f"- {name}: actual SHA-256 {actual}; manifest {expected}; match={actual==expected}.")
 lines += ["","TEST_SPLIT_TOUCH count: 0.",""]
out=ROOT/"reports/b10_2_ablation.md";out.write_text("\n".join(lines),encoding="utf-8")
print("\n".join(lines[:40]));print(f"Full report: {out}")
if __name__=="__main__":main()
