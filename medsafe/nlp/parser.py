"""Parse shorthand. strength is the product strength as written; for combination products it is not a per-ingredient dose. A future dose checker must not multiply it out for combination products unless per-ingredient strengths exist in CSV."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field, ValidationError

from medsafe.core.normalizer import normalize_drug
from medsafe.models.domain import MedOrder, UnresolvedItem


ROOT = Path(__file__).resolve().parents[2]
MAX_INPUT_CHARS = 5000
MAX_LINES = 50
MAX_LINE_CHARS = 300


class ParseLimitError(ValueError):
    """Input exceeded parser limits; caller should return HTTP 422."""


class UnparsedLine(BaseModel):
    line: str
    reason: str


class ParseResult(BaseModel):
    orders: list[MedOrder] = Field(default_factory=list)
    unparsed_lines: list[UnparsedLine] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def __iter__(self) -> Iterator[object]:
        """Preserve legacy two-value unpacking for existing callers."""
        checkable = self.orders_for_checking
        unresolved = [UnresolvedItem(item=item.line, reason=item.reason) for item in self.unparsed_lines]
        unresolved.extend(UnresolvedItem(item=order.drug_name,
            reason=f"Drug name did not resolve exactly; parsed fields retained: {order.model_dump_json()}")
            for order in self.orders if order not in checkable)
        yield checkable
        yield unresolved

    @property
    def orders_for_checking(self) -> list[MedOrder]:
        return [order for order in self.orders if _exact_result(order.name_used or order.drug_name)]


def _read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / "data/seed" / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


FREQUENCY_MAP = {row["code"].strip().upper(): row for row in _read_csv("frequency_map.csv")}
FORM_MAP = {row["token"].strip().casefold(): row for row in _read_csv("dosage_forms.csv")}
UNIT_ROWS = {row["token"].strip().casefold(): row for row in _read_csv("units.csv")}
UNIT_MAP = {token: row["canonical_unit"] for token, row in UNIT_ROWS.items()}
UNIT_KIND_MAP = {token: row["kind"].strip().upper() for token, row in UNIT_ROWS.items()}
_FORM_TOKENS = set(FORM_MAP)
_TOKEN_RE = re.compile(
    r"\d+(?:\.\d+)?(?:\s*(?:µg|mcg|ug|mg|ml|iu|g))?|"
    r"\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)+|[A-Za-zµ]+|[^\w\s]", re.I)
_SLOT_RE = re.compile(r"(?<!\w)\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)+(?!\w)")
_ROUTES = {"po": "oral", "oral": "oral", "iv": "iv", "im": "im",
           "sc": "sc", "topical": "topical"}
_DURATION_RE = re.compile(
    r"(?i)(?:\bx\s*\d+(?:\.\d+)?\s*(?:days?|d|weeks?|wks?)\b|"
    r"\bfor\s+\d+(?:\.\d+)?\s*(?:days?|d|weeks?|wks?)\b|"
    r"\b\d+(?:\.\d+)?\s*(?:days?|d|weeks?|wks?)\b)")
_MONTH_RE = re.compile(r"(?i)(?:\bx\s*|\bfor\s+)?\d+(?:\.\d+)?\s*months?\b")
_NUMBER_UNIT_RE = re.compile(r"^(\d+(?:\.\d+)?)(?:\s*)(µg|mcg|ug|mg|ml|iu|g)?$", re.I)


def _normal_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _explicit_brand_aliases() -> set[str]:
    aliases: set[str] = set()
    whitelist = ROOT / "data/seed/drug_whitelist.csv"
    aliases.update(_normal_key(line) for line in whitelist.read_text(encoding="utf-8-sig").splitlines()
                   if line.strip() and not line.lstrip().startswith("#"))
    for row in _read_csv("synonyms.csv"):
        if row.get("verified", "").strip().casefold() in {"yes", "true", "1"}:
            alias = row.get("alias", "").strip()
            if alias:
                aliases.add(_normal_key(alias))
    return aliases


_EXPLICIT_ALIASES = _explicit_brand_aliases()


def _exact_result(name: str):
    result = normalize_drug(name)
    if result.status == "matched" and result.confidence == 100:
        return result
    return None


def _exact_brand_match(candidate: str, number_token: str):
    combined = f"{candidate} {number_token}".strip()
    alias_key = _normal_key(re.sub(r"\s*(?:µg|mcg|ug|mg|ml|iu|g)\s*$", "", combined, flags=re.I))
    if alias_key not in _EXPLICIT_ALIASES:
        return None
    return _exact_result(combined)


def _split_comma_lines(text: str) -> list[str]:
    lines: list[str] = []
    leading_forms = "|".join(re.escape(token) for token in sorted(_FORM_TOKENS, key=len, reverse=True))
    start_form = re.compile(rf"(?i)^\s*(?:rx\s+)?(?:{leading_forms})\b")
    for group in re.split(r"[\n;]+", text):
        pieces = group.split(",")
        current = pieces[0]
        for piece in pieces[1:]:
            if start_form.search(piece):
                lines.append(current)
                current = piece
            else:
                current += "," + piece
        lines.append(current)
    return [line.strip() for line in lines if line.strip()]


def _remove_prefix(line: str) -> tuple[str, int]:
    marker_chars = 0
    line = re.sub(r"^\s*(?:\d+[).]|[-•])\s*", "", line)
    rx = re.match(r"(?i)^\s*rx\b\s*", line)
    if rx:
        marker_chars = rx.end()
        line = line[rx.end():]
    return line.strip(), marker_chars


def _token_form(token: str) -> dict[str, str] | None:
    return FORM_MAP.get(token.strip(".,:;()[]{}").casefold())


def _split_duration(line: str) -> tuple[int | None, tuple[int, int] | None, str | None]:
    month = _MONTH_RE.search(line)
    if month:
        return None, None, "Months are not supported for duration parsing."
    match = _DURATION_RE.search(line)
    if not match:
        return None, None, None
    number = re.search(r"\d+(?:\.\d+)?", match.group())
    if not number:
        return None, None, "Duration could not be read."
    amount = float(number.group())
    token = match.group().casefold()
    days = amount * (7 if any(unit in token for unit in ("week", "wk")) else 1)
    if not days.is_integer() or days <= 0:
        return None, match.span(), "Duration must resolve to a positive whole number of days."
    return int(days), match.span(), None


def _extract_line(original_line: str) -> tuple[MedOrder | None, UnparsedLine | None, list[str]]:
    line, _ = _remove_prefix(original_line)
    notes: list[str] = []
    tokens = list(_TOKEN_RE.finditer(line))
    consumed: set[int] = set()
    form: str | None = None
    route: str | None = None
    route_is_assumed = False

    first_word_index = next((i for i, token in enumerate(tokens)
                             if token.group().isalnum() or any(char.isalpha() for char in token.group())), None)
    if first_word_index is not None:
        form_row = _token_form(tokens[first_word_index].group())
        if form_row:
            form = form_row["canonical_form"]
            consumed.add(first_word_index)

    frequency_code: str | None = None
    frequency_per_day: float | None = None
    as_needed = False
    one_time = False
    slot_match = _SLOT_RE.search(line)
    occupied_spans: list[tuple[int, int]] = []
    if slot_match:
        occupied_spans.append(slot_match.span())
        slot_values = slot_match.group().split("-")
        try:
            nums = [float(value) for value in slot_values]
            valid_whole = all(number.is_integer() for number in nums)
        except ValueError:
            nums = []
            valid_whole = False
        nonzero = [int(number) for number in nums if number != 0] if valid_whole else []
        if not valid_whole:
            notes.append(f"Slot pattern '{slot_match.group()}' contains a non-whole or invalid slot.")
        elif nonzero and len(set(nonzero)) != 1:
            notes.append(f"Slot pattern '{slot_match.group()}' has unequal non-zero quantities; frequency unresolved.")
        elif nonzero:
            frequency_per_day = float(len(nonzero))
        for index, token in enumerate(tokens):
            if token.start() < slot_match.end() and token.end() > slot_match.start():
                consumed.add(index)

    frequency_pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(code) for code in
        sorted(FREQUENCY_MAP, key=len, reverse=True)) + r")(?!\w)", re.I)
    frequency_matches = [match for match in frequency_pattern.finditer(line)
                         if not any(start <= match.start() < end for start, end in occupied_spans)]
    for match in frequency_matches:
        for index, token in enumerate(tokens):
            if token.start() < match.end() and token.end() > match.start():
                consumed.add(index)
    frequency_rows = [(match, FREQUENCY_MAP[match.group().upper()]) for match in frequency_matches]
    as_needed_matches = [(match, row) for match, row in frequency_rows
                         if row["as_needed"].strip().casefold() == "true"]
    scheduled_matches = [(match, row) for match, row in frequency_rows
                         if row["as_needed"].strip().casefold() != "true"]
    scheduled_codes = list(dict.fromkeys(match.group().upper() for match, _ in scheduled_matches))
    slot_frequency = frequency_per_day
    frequency_conflict = False
    if scheduled_matches and as_needed_matches:
        first_scheduled = scheduled_matches[0][0].group()
        first_as_needed = as_needed_matches[0][0].group()
        frequency_code = " ".join(match.group() for match, _ in frequency_rows)
        frequency_per_day = None
        as_needed = True
        one_time = False
        frequency_conflict = True
        notes.append(f"Conflicting frequency tokens ({first_scheduled} and {first_as_needed}): "
                     "treated as as-needed with unknown maximum daily frequency.")
    elif len(scheduled_codes) > 1:
        first, second = scheduled_codes[:2]
        if slot_match:
            first = slot_match.group()
        frequency_code = None
        frequency_per_day = None
        one_time = False
        frequency_conflict = True
        notes.append(f"Conflicting scheduled frequency codes ({first}, {second}); frequency unresolved.")
    elif scheduled_matches:
        match, row = scheduled_matches[0]
        frequency_code = match.group().upper()
        frequency_per_day = float(row["times_per_day"]) if row["times_per_day"].strip() else None
        one_time = row["one_time"].strip().casefold() == "true"
        if row.get("note", "").strip():
            notes.append(row["note"].strip())
        if slot_match and slot_frequency is not None and frequency_per_day != slot_frequency:
            frequency_conflict = True
            frequency_code = None
            frequency_per_day = None
            notes.append(f"Conflicting scheduled frequency codes ({slot_match.group()}, {match.group().upper()}); "
                         "frequency unresolved.")
    elif as_needed_matches:
        match, row = as_needed_matches[0]
        frequency_code = match.group().upper()
        as_needed = True
        frequency_per_day = None
        one_time = row["one_time"].strip().casefold() == "true"
    if not frequency_conflict and len(frequency_rows) == 1 and slot_match and frequency_per_day is None:
        frequency_per_day = slot_frequency

    duration_days, duration_span, duration_note = _split_duration(line)
    if duration_span:
        occupied_spans.append(duration_span)
        for index, token in enumerate(tokens):
            if token.start() < duration_span[1] and token.end() > duration_span[0]:
                consumed.add(index)
    if duration_note:
        notes.append(duration_note)

    explicit_route_indices: list[int] = []
    for index, token in enumerate(tokens):
        route_value = _ROUTES.get(token.group().strip(".,:;()[]{}").casefold())
        if route_value:
            route = route_value
            explicit_route_indices.append(index)
            consumed.add(index)
    if form and not route:
        form_row = next(row for row in FORM_MAP.values() if row["canonical_form"] == form)
        route_hint = form_row["route_hint"].strip()
        if route_hint:
            route = route_hint
            route_is_assumed = form_row["route_is_assumed"].strip().casefold() == "true"

    # Candidate stops at first dose-like number, recognized direction, or route token.
    candidate_indices: list[int] = []
    for index, token in enumerate(tokens):
        if index in consumed:
            continue
        raw = token.group().strip(".,:;()[]{}")
        if not raw:
            continue
        if index == first_word_index and form:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?(?:\s*(?:µg|mcg|ug|mg|ml|iu|g))?", raw, re.I):
            break
        if raw.casefold() in FREQUENCY_MAP or raw.casefold() in _ROUTES or raw.casefold() in {"x", "for"}:
            break
        if raw.casefold() in _FORM_TOKENS:
            break
        if re.fullmatch(r"[a-zA-Zµ]+", raw):
            candidate_indices.append(index)
    candidate = " ".join(tokens[index].group().strip(".,:;()[]{}") for index in candidate_indices).strip()
    if not candidate:
        return None, UnparsedLine(line=original_line,
            reason="No medication name candidate found in line."), notes
    consumed.update(candidate_indices)

    # An explicit intake quantity is a number immediately followed by a dosage-form token.
    units_per_intake: float | None = None
    for index in range(len(tokens) - 1):
        if index in consumed:
            continue
        number_match = re.fullmatch(r"\d+(?:\.\d+)?", tokens[index].group())
        form_row = _token_form(tokens[index + 1].group())
        if number_match and form_row:
            units_per_intake = float(number_match.group())
            form = form or form_row["canonical_form"]
            consumed.update((index, index + 1))
            if form_row["route_hint"].strip() and not route:
                route = form_row["route_hint"].strip()
                route_is_assumed = form_row["route_is_assumed"].strip().casefold() == "true"
            break
    if slot_match and frequency_per_day is not None and not any("unequal" in note for note in notes):
        values = [int(float(value)) for value in slot_match.group().split("-") if float(value) != 0]
        if values:
            slot_units = float(values[0])
            if units_per_intake is not None and units_per_intake != slot_units:
                notes.append("Units per intake conflict between quantity and slot pattern; unresolved.")
                units_per_intake = None
            else:
                units_per_intake = slot_units
    elif slot_match and frequency_per_day is None and not any("Slot pattern" in note for note in notes):
        notes.append(f"Slot pattern '{slot_match.group()}' could not be resolved.")

    number_token_index: int | None = None
    number_value: float | None = None
    number_unit: str | None = None
    for index, token in enumerate(tokens):
        if index in consumed:
            continue
        parsed = _NUMBER_UNIT_RE.fullmatch(token.group().strip())
        if parsed:
            number_token_index = index
            number_value = float(parsed.group(1))
            raw_unit = (parsed.group(2) or "").casefold()
            number_unit = UNIT_MAP.get(raw_unit) if raw_unit else None
            break

    brand_match = None
    if number_token_index is not None and number_value is not None:
        brand_match = _exact_brand_match(candidate, tokens[number_token_index].group().strip())
    name_result = brand_match or _exact_result(candidate)
    if brand_match:
        name_used = " ".join((candidate, tokens[number_token_index].group().strip()))
        consumed.add(number_token_index)
    else:
        name_used = candidate

    strength_value: float | None = None
    strength_unit: str | None = None
    unit_kind: str | None = None
    if number_token_index is not None and number_token_index not in consumed:
        if number_unit:
            strength_value = number_value
            strength_unit = number_unit
            unit_kind = UNIT_KIND_MAP.get((parsed.group(2) or "").casefold())
            consumed.add(number_token_index)
        elif number_value is not None:
            next_index = number_token_index + 1
            if next_index < len(tokens) and tokens[next_index].group().strip().casefold() in UNIT_MAP:
                raw_unit = tokens[next_index].group().strip().casefold()
                strength_value = number_value
                strength_unit = UNIT_MAP[raw_unit]
                unit_kind = UNIT_KIND_MAP.get(raw_unit)
                consumed.update((number_token_index, next_index))
            elif next_index < len(tokens) and _token_form(tokens[next_index].group()):
                pass  # This is an explicit units-per-intake quantity, not a strength.
            else:
                notes.append(f"Bare number '{tokens[number_token_index].group()}' is ambiguous; not treated as mg.")
                consumed.add(number_token_index)

    # Unit separated from its numeric token belongs to an adjacent number only.
    for index, token in enumerate(tokens):
        raw = token.group().strip().casefold()
        if raw in UNIT_MAP and ((index > 0 and index - 1 in consumed) or (index in consumed)):
            consumed.add(index)

    has_frequency = frequency_code is not None or frequency_per_day is not None
    if not has_frequency and not as_needed and not one_time:
        notes.append("frequency not stated or unresolved")
    if units_per_intake is None:
        notes.append("quantity per intake not stated")
    if unit_kind == "VOLUME":
        notes.append("Volume stated; concentration (mass per volume) not stated; cannot convert to mass.")
    if form and not route:
        route_row = next(row for row in FORM_MAP.values() if row["canonical_form"] == form)
        if route_row["route_hint"].strip():
            route = route_row["route_hint"].strip()
            route_is_assumed = route_row["route_is_assumed"].strip().casefold() == "true"

    unparsed_tokens = [token.group().strip() for index, token in enumerate(tokens)
                       if index not in consumed and token.group().strip(".,:;()[]{}")]
    if name_result is None:
        # Keep unmatched candidate as an order so API report can retain parsed details.
        name_used = name_used or candidate
        notes.append("Drug name did not resolve exactly; no medication checks applied.")
    no_leftovers = not unparsed_tokens
    has_strength_or_brand = strength_value is not None or brand_match is not None
    resolved = name_result is not None
    if (resolved and has_strength_or_brand and has_frequency and no_leftovers
            and not frequency_conflict and not any("ambiguous" in note for note in notes)):
        confidence = "HIGH"
    elif resolved and has_frequency:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    order = MedOrder(drug_name=name_used if brand_match else candidate,
        dose_value=strength_value, dose_unit=strength_unit,
        unit_kind=unit_kind,
        frequency_per_day=frequency_per_day, route=route, duration_days=duration_days,
        form=form,
        units_per_intake=units_per_intake, frequency_code=frequency_code,
        as_needed=as_needed, one_time=one_time, route_is_assumed=route_is_assumed,
        parse_confidence=confidence, parse_notes=notes, unparsed_tokens=unparsed_tokens,
        source_line=original_line, name_used=name_used)
    return order, None, notes


def parse_prescription(text: str) -> ParseResult:
    if len(text) > MAX_INPUT_CHARS:
        raise ParseLimitError(f"Prescription text exceeds {MAX_INPUT_CHARS} characters.")
    source_lines = text.splitlines() or ([text] if text else [])
    if len(source_lines) > MAX_LINES:
        raise ParseLimitError(f"Prescription text exceeds {MAX_LINES} lines.")
    if any(len(line) > MAX_LINE_CHARS for line in source_lines):
        raise ParseLimitError(f"Prescription line exceeds {MAX_LINE_CHARS} characters.")
    lines = _split_comma_lines(text)
    if len(lines) > MAX_LINES:
        raise ParseLimitError(f"Prescription text exceeds {MAX_LINES} parsed lines.")
    orders: list[MedOrder] = []
    unparsed: list[UnparsedLine] = []
    notes: list[str] = []
    for raw_line in lines:
        try:
            order, failed, line_notes = _extract_line(raw_line)
        except (ValidationError, ValueError, IndexError) as error:
            order, failed, line_notes = None, UnparsedLine(line=raw_line,
                reason=f"Could not parse line: {error}"), []
        notes.extend(line_notes)
        if order:
            orders.append(order)
        if failed:
            unparsed.append(failed)
    return ParseResult(orders=orders, unparsed_lines=unparsed, notes=notes)
