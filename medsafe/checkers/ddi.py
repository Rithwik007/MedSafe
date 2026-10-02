"""Deterministic DDI checker with combination-product expansion."""
from __future__ import annotations

from collections import defaultdict
from typing import TypedDict

from medsafe.checkers.ingredients import IngredientOrder, comparison_pairs, expand_orders, ingredient_key
from medsafe.kb.rules import RULES, Rule
from medsafe.models.domain import Finding, FindingType, Prescription, Severity
from medsafe.core.ingredient_names import display_name


def _display_ingredient(name: str) -> str:
    return display_name(name)


class PairMatches(TypedDict):
    rule: Rule
    orders: dict[tuple[bool, int], IngredientOrder]

SEVERITY_RANK = {
    Severity.CONTRAINDICATED: 5,
    Severity.MAJOR: 4,
    Severity.MODERATE: 3,
    Severity.MINOR: 2,
    Severity.UNSPECIFIED: 1,
    Severity.INFO: 0,
}


def _rule_pair(rule: Rule) -> tuple[str, str] | None:
    if rule.kind != FindingType.DDI or len(rule.drugs) != 2:
        return None
    return tuple(sorted((ingredient_key(rule.drugs[0]), ingredient_key(rule.drugs[1]))))


def _matches(left: IngredientOrder, right: IngredientOrder, pair: tuple[str, str]) -> bool:
    for a in left.ingredients:
        for b in right.ingredients:
            if tuple(sorted((a.key, b.key))) == pair and a.key != b.key:
                return True
    return False


def check_ddi(prescription: Prescription, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    expanded, _ = expand_orders(prescription)
    pairs = comparison_pairs(expanded)
    grouped: dict[tuple[str, str], PairMatches] = {}
    for rule in rules:
        pair = _rule_pair(rule)
        if pair is None or rule.evidence.review_status not in {
                "reviewed", "dataset_imported_not_independently_clinically_reviewed"}:
            continue
        matched_orders = [order for left, right in pairs if _matches(left, right, pair)
                          for order in (left, right)]
        if not matched_orders:
            continue
        item = grouped.get(pair)
        if item is None:
            item = {"rule": rule, "orders": {}}
            grouped[pair] = item
        current = item["rule"]
        if (SEVERITY_RANK[rule.severity] > SEVERITY_RANK[current.severity]
                or (rule.severity == current.severity and rule.rule_id < current.rule_id)):
            item["rule"] = rule
        order_map = item["orders"]
        for order in matched_orders:
            order_map[(order.is_new, order.index)] = order

    findings: list[Finding] = []
    for item in grouped.values():
        rule = item["rule"]
        orders = sorted(item["orders"].values(), key=lambda value: (value.is_new, value.index))
        order_names = [order.display_name for order in orders]
        if rule.severity == Severity.UNSPECIFIED:
            reason = "Interaction reported by DDInter without a severity classification; requires pharmacist review."
            recommendation = "Pharmacist review required; consult an authoritative clinical source before action."
        else:
            reason = rule.reason
            recommendation = rule.recommendation or "Review source record and confirm appropriate management with a qualified clinician."
        display_pair = [_display_ingredient(name) for name in rule.drugs]
        reason += f" Ingredient pair: {display_pair[0]} + {display_pair[1]}. Orders involved: {', '.join(order_names)}."
        findings.append(Finding(type=rule.kind, severity=rule.severity, drugs_involved=order_names,
            reason=reason, mechanism=rule.mechanism or None, recommendation=recommendation,
            rule_id=rule.rule_id, evidence=rule.evidence))
    return findings
