"""Offline answer-match proxies; semantic faithfulness is never inferred."""

import re
from decimal import Decimal

from finsight.contracts import Answer

from .normalization import OCCURRENCE, normalize_text, parse_quantity, quantities

SCORER_VERSION = "financial-match-v1"
RELATIVE_TOLERANCE = Decimal("0.001")
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
QUARTER = re.compile(
    r"\bq[1-4]\b|\b(?:first|second|third|fourth|[1-4](?:st|nd|rd|th))\s+quarter\b",
    re.I,
)
QUARTER_NAMES = {"first": "q1", "second": "q2", "third": "q3", "fourth": "q4"}


def _quarters(text):
    return {
        QUARTER_NAMES.get(m[0].lower().split()[0], "q" + m[0][0])
        if not m[0].lower().startswith("q")
        else m[0].lower()
        for m in QUARTER.finditer(text)
    }


def _period_years(text):
    financial_spans = [
        m.span()
        for m in OCCURRENCE.finditer(text)
        if (q := parse_quantity(m[0])) is not None
        and not (q.unit == "number" and m[0].strip() == str(q.value))
    ]
    return [
        m
        for m in YEAR.finditer(text)
        if not any(start <= m.start() and m.end() <= end for start, end in financial_spans)
    ]


def score_answer(
    answer: Answer, reference: str, *, question: str = "", period: str | None = None
) -> dict:
    result = dict(
        match=None, method="needs_review", reason="complex_reference", claim_faithfulness=None
    )
    if answer.status == "error":
        return {**result, "reason": "operational_error"}
    if answer.status == "partial":
        return {**result, "reason": "partial_answer"}
    if answer.status == "insufficient_evidence":
        return {**result, "match": False, "method": "abstention", "reason": "answer_expected"}
    expected, actual = normalize_text(reference), normalize_text(answer.answer_text)
    if expected == actual:
        return {**result, "match": True, "method": "exact_text", "reason": "normalized_text_equal"}
    booleans = {"yes": True, "true": True, "no": False, "false": False}
    if expected in booleans:
        if actual not in booleans:
            return {**result, "reason": "boolean_explanation_requires_review"}
        return {
            **result,
            "match": booleans[expected] == booleans[actual],
            "method": "boolean",
            "reason": "short_boolean",
        }
    gold = parse_quantity(reference)
    if gold is None:
        return result
    years = {m[0] for m in _period_years(question)} or set(YEAR.findall(period or ""))
    actual_years = {m[0] for m in _period_years(actual)}
    quarters, actual_quarters = _quarters(question), _quarters(actual)
    if (
        len(years) > 1
        or len(quarters) > 1
        or (actual_years and (not years or actual_years != years))
        or (actual_quarters and actual_quarters != quarters)
        or re.search(r"\bfy\s*['’]?\d{2}\b", actual)
    ):
        return {**result, "reason": "ambiguous_or_conflicting_period"}
    if re.search(
        r"\b(?:not|never|neither|roughly|about|approximately)\b|"
        r"\b(?:more|less|greater|fewer)\s+than\b|\bat\s+(?:least|most)\b|[<>≤≥]",
        actual,
    ):
        return {**result, "reason": "qualified_or_negated_quantity"}
    # Period markers are validated independently before removal, including FY2022
    # and Q1. Bare years remain visible so numeric years cannot be silently lost.
    numeric_text = QUARTER.sub(" ", actual)
    numeric_text = re.sub(r"\bfy\s*((?:19|20)\d{2})\b", r"\1", numeric_text)
    for match in reversed(_period_years(numeric_text)):
        if gold.unit != "number" or Decimal(match[0]) != gold.value:
            numeric_text = numeric_text[: match.start()] + " " + numeric_text[match.end() :]
    found = quantities(numeric_text)
    years = {Decimal(y) for y in years}
    found = tuple(q for q in found if not (q.unit == "number" and q.value in years and q != gold))
    if not found:
        return {**result, "reason": "no_unambiguous_quantity"}
    comparisons = []
    for quantity in found:
        if quantity.unit != gold.unit:
            comparisons.append(None if "number" in {quantity.unit, gold.unit} else False)
        else:
            comparisons.append(
                abs(quantity.value - gold.value) <= abs(gold.value) * RELATIVE_TOLERANCE
            )
    if all(c is True for c in comparisons):
        return {**result, "match": True, "method": "numeric", "reason": "value_and_unit_match"}
    if len(comparisons) == 1 and comparisons[0] is False:
        return {**result, "match": False, "method": "numeric", "reason": "value_or_unit_mismatch"}
    return {**result, "reason": "multiple_quantities_or_ambiguous_units"}
