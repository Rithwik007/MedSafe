"""Rule-configured duplicate ingredient and ATC-class warnings."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from medsafe.checkers.ingredients import IngredientOrder, comparison_pairs, expand_orders
from medsafe.core.normalizer import normalize_drug
from medsafe.models.domain import Evidence, Finding, FindingType, Prescription, SafetyReport, Severity

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "data/seed/duplicate_policy.csv"
ATC_PATH = ROOT / "data/seed/drug_classes.csv"


def load_policy(path: Path = POLICY_PATH) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["level"].strip().upper(): row for row in csv.DictReader(stream)}


def load_atc_codes(path: Path = ATC_PATH) -> dict[str, set[str]]:
    codes: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if (row.get("class") or "").strip() == "TODO_VERIFY":
                continue
            key = normalize_drug(row.get("drug", ""))
            ingredient = key.canonical.casefold() if key.canonical else " ".join(row["drug"].casefold().split())
            codes[ingredient].update(code.strip() for code in (row.get("atc_code") or "").split("|") if code.strip())
    return codes


def _finding(policy: dict[str, str], rule_suffix: str, names: list[str], reason: str) -> Finding:
    return Finding(type=FindingType.DUPLICATE, severity=Severity(policy["severity"].strip().upper()),
        drugs_involved=names, reason=reason, recommendation=policy["recommendation"],
        rule_id=f"DUPLICATE-POLICY-{rule_suffix}",
        evidence=Evidence(source_name="duplicate_policy.csv", review_status=policy["status"],
                          review_label="Not reviewed", rationale=policy["rationale"]))


def check_duplicates(prescription: Prescription, policy_path: Path = POLICY_PATH,
                     atc_path: Path = ATC_PATH) -> SafetyReport:
    policies = load_policy(policy_path)
    orders, unresolved = expand_orders(prescription)
    pairs = comparison_pairs(orders)
    findings: list[Finding] = []
    ingredient_occurrences: dict[str, dict[int, tuple[IngredientOrder, str]]] = defaultdict(dict)

    for left, right in pairs:
        for a in left.ingredients:
            for b in right.ingredients:
                if a.key == b.key:
                    ingredient_occurrences[a.key][id(left)] = (left, a.name)
                    ingredient_occurrences[a.key][id(right)] = (right, b.name)

    policy = policies["INGREDIENT"]
    for ingredient, hits in ingredient_occurrences.items():
        matched = sorted(hits.values(), key=lambda entry: (entry[0].is_new, entry[0].index))
        if len(matched) < 2:
            continue
        names = [item.display_name for item, _ in matched]
        first_name, second_name = names[0], names[1]
        display = matched[0][1]
        reason = policy["message_template"].format(ingredient=display,
            order_a=first_name, order_b=second_name)
        details = "; ".join(f"{'New' if item.is_new else 'Current'} order {item.index + 1} ({item.display_name}) contains {name}"
                             for item, name in matched)
        reason += f"\nOrders involved: {details}."
        findings.append(_finding(policy, "INGREDIENT", names, reason))

    atc_policy = policies["ATC_CLASS"]
    prefix_length = int(atc_policy["atc_prefix_length"])
    atc_codes = load_atc_codes(atc_path)
    class_hits: dict[tuple[str, str, str], dict[int, IngredientOrder]] = defaultdict(dict)
    class_names: dict[tuple[str, str, str], tuple[str, str]] = {}
    for left, right in pairs:
        for a in left.ingredients:
            for b in right.ingredients:
                if a.key == b.key:
                    continue
                shared = {code[:prefix_length] for code in atc_codes.get(a.key, set()) if len(code) >= prefix_length}
                shared &= {code[:prefix_length] for code in atc_codes.get(b.key, set()) if len(code) >= prefix_length}
                for code in shared:
                    key = (code, *sorted((a.key, b.key)))
                    class_hits[key][id(left)] = left
                    class_hits[key][id(right)] = right
                    class_names[key] = (a.name, b.name)

    for key, hits in class_hits.items():
        code, _, _ = key
        left_ingredient, right_ingredient = class_names[key]
        matched_orders = sorted(hits.values(), key=lambda item: (item.is_new, item.index))
        names = [item.display_name for item in matched_orders]
        if len(names) < 2:
            continue
        reason = atc_policy["message_template"].format(ingredient_a=left_ingredient,
            ingredient_b=right_ingredient, atc_code=code, order_a=names[0], order_b=names[1])
        details = "; ".join(f"{'New' if item.is_new else 'Current'} order {item.index + 1} ({item.display_name})"
                             for item in matched_orders)
        reason += f"\nOrders involved: {details}."
        findings.append(_finding(atc_policy, "ATC-CLASS", names, reason))
    return SafetyReport(findings=findings, unresolved_items=unresolved)
