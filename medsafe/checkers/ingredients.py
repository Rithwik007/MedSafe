"""Expand source orders into curated active ingredients."""
from dataclasses import dataclass

from medsafe.core.normalizer import normalize_drug
from medsafe.core.ingredient_names import display_name
from medsafe.models.domain import MedOrder, Prescription, UnresolvedItem


@dataclass(frozen=True)
class Ingredient:
    name: str
    key: str


@dataclass(frozen=True)
class IngredientOrder:
    order: MedOrder
    is_new: bool
    index: int
    ingredients: tuple[Ingredient, ...]

    @property
    def display_name(self) -> str:
        return self.order.drug_name


def ingredient_key(name: str) -> str:
    result = normalize_drug(name)
    if result.canonical:
        return result.canonical.casefold()
    return " ".join(name.casefold().split())


def expand_orders(prescription: Prescription) -> tuple[list[IngredientOrder], list[UnresolvedItem]]:
    expanded: list[IngredientOrder] = []
    unresolved: list[UnresolvedItem] = []
    for is_new, orders in ((False, prescription.patient.current_meds), (True, prescription.new_orders)):
        for index, order in enumerate(orders):
            result = normalize_drug(order.drug_name)
            if result.status != "matched" or not result.ingredients:
                unresolved.append(UnresolvedItem(item=order.drug_name,
                    reason="Drug name not in curated alias list; no clinical checks applied."))
                continue
            ingredients = tuple(Ingredient(name=display_name(name), key=ingredient_key(name))
                                for name in result.ingredients)
            expanded.append(IngredientOrder(order=order, is_new=is_new, index=index,
                                            ingredients=ingredients))
    return expanded, unresolved


def comparison_pairs(orders: list[IngredientOrder]) -> list[tuple[IngredientOrder, IngredientOrder]]:
    current = [order for order in orders if not order.is_new]
    new = [order for order in orders if order.is_new]
    pairs = [(added, existing) for added in new for existing in current]
    pairs.extend((new[left], new[right]) for left in range(len(new))
                 for right in range(left + 1, len(new)))
    return pairs
