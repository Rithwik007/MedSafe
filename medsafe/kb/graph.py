"""Typed knowledge graph from curated medication-safety CSV files."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import networkx as nx

ROOT = Path(__file__).resolve().parents[2]


class KnowledgeGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self.class_rules: list[dict[str, str]] = []

    @classmethod
    def load(cls, class_path: Path | None = None, rules_path: Path | None = None,
             class_rules_path: Path | None = None) -> "KnowledgeGraph":
        result = cls()
        class_path = class_path or ROOT / "data/seed/drug_classes.csv"
        rules_path = rules_path or ROOT / "data/seed/rules.csv"
        class_rules_path = class_rules_path or ROOT / "data/seed/class_rules.csv"
        if class_path.exists():
            with class_path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    drug = (row.get("drug") or "").strip()
                    class_name = (row.get("class") or "").strip()
                    if not drug:
                        continue
                    drug_node = result._node("drug", drug)
                    if class_name and class_name != "TODO_VERIFY":
                        classes = [part.strip() for part in class_name.split("|") if part.strip()]
                        codes = [part.strip() for part in (row.get("atc_code") or "").split("|")]
                        for index, value in enumerate(classes):
                            class_node = result._node("class", value)
                            result.graph.add_edge(drug_node, class_node, type="member_of",
                                atc_code=codes[index] if index < len(codes) else None,
                                source=(row.get("source") or "").strip() or None)
        if rules_path.exists():
            with rules_path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    drugs = [x.strip() for x in (row.get("drugs") or "").split("|") if x.strip()]
                    kind = (row.get("type") or "").strip().upper()
                    if kind == "DDI" and len(drugs) == 2:
                        a, b = (result._node("drug", name) for name in drugs)
                        result.graph.add_edge(a, b, type="interacts_with", rule_id=row.get("rule_id"),
                            severity=row.get("severity"), source_url=row.get("source_url"))
                        result.graph.add_edge(b, a, type="interacts_with", rule_id=row.get("rule_id"),
                            severity=row.get("severity"), source_url=row.get("source_url"))
                    elif kind in {"DRUG_DISEASE", "ALLERGY"} and len(drugs) == 1:
                        trigger = (row.get("trigger") or "").strip()
                        if trigger:
                            entity_type = "condition" if kind == "DRUG_DISEASE" else "allergen"
                            entity = result._node(entity_type, trigger)
                            result.graph.add_edge(result._node("drug", drugs[0]), entity,
                                type=kind.lower(), rule_id=row.get("rule_id"), severity=row.get("severity"),
                                source_url=row.get("source_url"))
        if class_rules_path.exists():
            with class_rules_path.open(encoding="utf-8-sig", newline="") as stream:
                result.class_rules = [row for row in csv.DictReader(stream)
                    if row.get("rule_id") and row.get("class_a") and row.get("class_b")]
        return result

    def _node(self, kind: str, label: str) -> str:
        node = f"{kind}:{label.casefold()}"
        self.graph.add_node(node, type=kind, label=label)
        return node

    @staticmethod
    def _key(value: str) -> str:
        if ":" in value:
            kind, label = value.split(":", 1)
            return f"{kind.casefold()}:{label.casefold()}"
        return f"drug:{value.casefold()}"

    def get_class(self, drug: str) -> tuple[str, ...]:
        node = self._key(drug)
        if node not in self.graph:
            return ()
        return tuple(sorted(self.graph.nodes[n]["label"] for n in self.graph.successors(node)
            if self.graph.edges[node, n].get("type") == "member_of"))

    def neighbors_by_type(self, node: str, node_type: str | None = None,
                          edge_type: str | None = None) -> list[dict[str, Any]]:
        key = self._key(node)
        if key not in self.graph:
            return []
        found = []
        for neighbor in self.graph.successors(key):
            edge = self.graph.edges[key, neighbor]
            attrs = self.graph.nodes[neighbor]
            if node_type and attrs.get("type") != node_type:
                continue
            if edge_type and edge.get("type") != edge_type:
                continue
            found.append({"label": attrs.get("label"), "type": attrs.get("type"), **edge})
        return found

    def find_path(self, source: str, target: str) -> list[str] | None:
        try:
            path = nx.shortest_path(self.graph, self._key(source), self._key(target))
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return None
        return [self.graph.nodes[node].get("label", node) for node in path]

    def matching_class_rules(self, drug_a: str, drug_b: str) -> list[dict[str, str]]:
        classes_a, classes_b = set(self.get_class(drug_a)), set(self.get_class(drug_b))
        return [rule for rule in self.class_rules if
            (rule["class_a"] in classes_a and rule["class_b"] in classes_b)
            or (rule["class_b"] in classes_a and rule["class_a"] in classes_b)]


def load_graph(**kwargs: Path) -> KnowledgeGraph:
    return KnowledgeGraph.load(**kwargs)
