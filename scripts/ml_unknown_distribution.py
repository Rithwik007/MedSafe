from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.stats import spearmanr
from medsafe.ml.data import load_ddinter
from medsafe.ml.features import pair_features
from medsafe.ml.predict import load_model
from medsafe.ml.splits import make_splits

def _predict_unknown(model, unknown):
    results = [(row.drug_a.casefold(), row.drug_b.casefold(), "Abstained")
               for row in unknown.itertuples(index=False)]
    eligible = []
    positions = []
    for i, (a,b,_) in enumerate(results):
        pair = tuple(sorted((a,b)))
        if a in model.vectors.vectors and b in model.vectors.vectors and pair in model.listed_pairs and pair in model.unlabeled_pairs:
            eligible.append(pair_features(a,b,model.vectors))
            positions.append(i)
    if eligible:
        probabilities = model.classifier.predict_proba(np.vstack(eligible))
        classes = model.classifier.classes_
        for pos, row in zip(positions, probabilities):
            idx = int(np.argmax(row))
            if float(row[idx]) >= model.tau:
                a,b,_ = results[pos]
                results[pos] = (a,b,str(classes[idx]).title())
    return results

def main() -> None:
    audit = load_ddinter()
    model = load_model()
    if not model.enabled:
        raise SystemExit("Shipped model gate is disabled.")
    whitelist = sorted((x.casefold() for x in audit.whitelist_present))
    predictions = _predict_unknown(model, audit.unlabeled_pairs)
    per_drug = {}
    for drug in whitelist:
        pairs = [e for e in predictions if drug in e[:2]]
        counts = {label: sum(e[2] == label for e in pairs)
                  for label in ("Major", "Moderate", "Minor", "Abstained")}
        n = len(pairs)
        per_drug[drug] = {**counts, "n": n,
            **{f"{label.lower()}_share": counts[label]/n if n else 0.0 for label in counts}}
    major_edges = [e for e in predictions if e[2] == "Major"]
    top_major = sorted(whitelist, key=lambda d: (-per_drug[d]["major_share"], d))[:5]

    train = make_splits(audit.labeled_pairs)["RANDOM_PAIR"].train
    train_shares = {}
    train_counts = {}
    for drug in whitelist:
        relevant = train.loc[(train.drug_a.str.casefold() == drug) |
                             (train.drug_b.str.casefold() == drug)]
        train_counts[drug] = len(relevant)
        train_shares[drug] = float(relevant.severity.eq("Major").mean()) if len(relevant) else 0.0
    values = [(per_drug[d]["major_share"], train_shares[d]) for d in whitelist
              if per_drug[d]["n"] > 0 and train_counts[d] > 0]
    corr = spearmanr([v[0] for v in values], [v[1] for v in values]) if len(values) >= 2 else None

    lines = ["# Unknown-pair model output by whitelist drug", "",
        "Per-drug denominators include every DDInter Unknown pair involving each whitelist drug, including partners outside the whitelist. A pair without a score at or above the shipped validation threshold is counted as abstained. Model and threshold are unchanged.", "",
        "| Drug | Unknown pairs | Major | Major share | Moderate | Moderate share | Minor | Minor share | Abstained | Abstained share | Labeled training pairs | Training Major share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for drug in whitelist:
        x = per_drug[drug]
        lines.append(f"| {drug} | {x['n']} | {x['Major']} | {x['major_share']:.3f} | {x['Moderate']} | {x['moderate_share']:.3f} | {x['Minor']} | {x['minor_share']:.3f} | {x['Abstained']} | {x['abstained_share']:.3f} | {train_counts[drug]} | {train_shares[drug]:.3f} |")
    total_pairs = len(predictions)
    totals = {label: sum(e[2] == label for e in predictions)
              for label in ("Major","Moderate","Minor","Abstained")}
    lines += ["", "## Overall totals", "",
        f"- DDInter Unknown pairs: {total_pairs}",
        f"- Major: {totals['Major']} ({totals['Major']/total_pairs if total_pairs else 0:.3f})",
        f"- Moderate: {totals['Moderate']} ({totals['Moderate']/total_pairs if total_pairs else 0:.3f})",
        f"- Minor: {totals['Minor']} ({totals['Minor']/total_pairs if total_pairs else 0:.3f})",
        f"- Abstained: {totals['Abstained']} ({totals['Abstained']/total_pairs if total_pairs else 0:.3f})",
        "", "## Top five whitelist drugs by Major share", "",
        "| Drug | Unknown pairs involving drug | Major | Major share |",
        "|---|---:|---:|---:|"]
    for drug in top_major:
        x=per_drug[drug]; lines.append(f"| {drug} | {x['n']} | {x['Major']} | {x['major_share']:.3f} |")
    lines += ["", "## Major-prediction concentration", "",
        f"Covered Unknown pairs with Major estimate: {len(major_edges)}.", "",
        "| Top drug | Major estimates involving drug | Share of all Major estimates |",
        "|---|---:|---:|"]
    for drug in top_major:
        n=sum(drug in e[:2] for e in major_edges)
        lines.append(f"| {drug} | {n} | {n/len(major_edges) if major_edges else 0:.3f} |")
    lines += ["", "## Major-share comparison and correlation", "",
        "Comparison uses labeled RANDOM_PAIR training edges only; no validation or test labels enter these per-drug history values.", "",
        "| Drug | Unknown-pair predicted Major share | Labeled training-pair Major share |",
        "|---|---:|---:|"]
    for drug in whitelist:
        lines.append(f"| {drug} | {per_drug[drug]['major_share']:.3f} | {train_shares[drug]:.3f} |")
    if corr:
        lines += ["", f"Spearman correlation across {len(values)} drugs with both denominators nonzero: "
            f"rho={corr.statistic:.4f}, p={corr.pvalue:.4g}."]
    else: lines += ["", "Spearman correlation unavailable (fewer than two comparable drugs)."]
    lines += ["", "Data limitation: the Unknown allowlist and labeled training-pair history are DDInter-derived. This report describes model output distribution, not clinical validity.", ""]
    path=ROOT/"reports/ml_unknown_distribution.md"
    path.write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()

