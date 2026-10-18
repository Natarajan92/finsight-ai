"""Financial arithmetic uses cited literals and Decimal, never executable expressions."""

import importlib
from decimal import Decimal

import pytest

from finsight.contracts import QueryRequest
from finsight.contracts.generation import DraftCalculation
from finsight.runtime.errors import FinsightError


def validator():
    assert importlib.util.find_spec("finsight.citations.calculation"), "Missing Decimal validation"
    return importlib.import_module("finsight.citations.calculation").validate_calculation


def calculation(**changes):
    data = dict(
        operator="subtract",
        operands=[
            dict(
                name="a",
                evidence_id="a" * 64,
                source_text="100",
                value="100",
                unit="USD millions",
                period="2022",
            ),
            dict(
                name="b",
                evidence_id="b" * 64,
                source_text="125",
                value="125",
                unit="USD millions",
                period="2021",
            ),
        ],
        result="-25",
        unit="USD millions",
    )
    data.update(changes)
    return DraftCalculation(**data)


def test_explicit_cross_period_subtraction_keeps_each_cited_year(citation_setup):
    packet, pages, _, _ = citation_setup
    result = validator()(
        calculation(),
        packet,
        pages,
        request=QueryRequest(question="What is the change in revenue from 2021 to 2022?"),
    )
    assert result.result == Decimal("-25")
    assert result.operands == {"a": Decimal("100"), "b": Decimal("125")}
    assert result.unit == "USD millions" and result.expression == "a - b"
    with pytest.raises(FinsightError, match="calculation_validation_failed"):
        validator()(calculation(), packet, pages)


@pytest.mark.parametrize(
    "change",
    [
        {"value": Decimal("999")},
        {"source_text": "1e2"},
        {"source_text": "__import__('os')"},
        {"unit": "EUR millions"},
        {"period": "2020"},
        {"evidence_id": "forged"},
    ],
)
def test_invented_numeric_value_unit_period_or_code_rejected(citation_setup, change):
    packet, pages, _, _ = citation_setup
    draft = calculation()
    operands = (draft.operands[0].model_copy(update=change), draft.operands[1])
    with pytest.raises(FinsightError, match="calculation_validation_failed"):
        validator()(
            draft.model_copy(update={"operands": operands}),
            packet,
            pages,
            request=QueryRequest(question="Compare 2021 and 2022 revenue"),
        )


def test_parentheses_negative_is_not_positive(citation_setup):
    packet, pages, _, _ = citation_setup
    draft = calculation(operator="add", result="100")
    a = draft.operands[0].model_copy(
        update={
            "evidence_id": "b" * 64,
            "source_text": "(25)",
            "value": Decimal("-25"),
            "period": "2021",
        }
    )
    draft = draft.model_copy(update={"operands": (a, draft.operands[1])})
    assert validator()(draft, packet, pages).result == 100
    with pytest.raises(FinsightError, match="calculation_validation_failed"):
        validator()(
            draft.model_copy(
                update={
                    "operands": (a.model_copy(update={"value": Decimal(25)}), draft.operands[1])
                }
            ),
            packet,
            pages,
        )


def test_dimensionless_multiplication_and_same_unit_division(citation_setup):
    packet, pages, _, _ = citation_setup
    draft = calculation(operator="multiply", result="200")
    b = draft.operands[1].model_copy(
        update={
            "evidence_id": "f" * 64,
            "source_text": "2",
            "value": Decimal(2),
            "unit": "dimensionless",
            "period": "2022",
        }
    )
    assert (
        validator()(
            draft.model_copy(update={"operands": (draft.operands[0], b)}), packet, pages
        ).result
        == 200
    )
    ratio = calculation(operator="divide", result="0.8", unit="dimensionless")
    assert validator()(
        ratio,
        packet,
        pages,
        request=QueryRequest(question="Compare 2021 and 2022 revenue as a ratio"),
    ).result == Decimal("0.8")


@pytest.mark.parametrize(
    "literal,value", [("1,000", "1000"), ("-25", "-25"), ("(25)", "-25"), ("1.25", "1.25")]
)
def test_explicit_financial_literal_parser(literal, value):
    validator()
    module = importlib.import_module("finsight.citations.calculation")
    assert module.parse_financial_literal(literal) == Decimal(value)


def test_mismatched_result_incompatible_units_and_division_zero_rejected(citation_setup):
    packet, pages, _, _ = citation_setup
    for draft in [calculation(result="-30"), calculation(operator="multiply", result="12500")]:
        with pytest.raises(FinsightError, match="calculation_validation_failed"):
            validator()(
                draft, packet, pages, request=QueryRequest(question="Compare 2021 and 2022")
            )
    # Zero is absent from the cited span; both invented operands and zero division fail closed.
    draft = calculation(operator="divide", unit="dimensionless", result="0")
    b = draft.operands[1].model_copy(update={"source_text": "0", "value": Decimal(0)})
    with pytest.raises(FinsightError, match="calculation_validation_failed"):
        validator()(
            draft.model_copy(update={"operands": (draft.operands[0], b)}),
            packet,
            pages,
            request=QueryRequest(question="Compare 2021 and 2022"),
        )


@pytest.mark.parametrize(
    "text,value,result", [("0", "0", "0"), ("3", "3", "33.33333333333333333333333333")]
)
def test_cited_zero_division_and_implicit_rounding_rejected(citation_setup, text, value, result):
    packet, pages, _, _ = citation_setup
    draft = calculation(operator="divide", result=result)
    b = draft.operands[1].model_copy(
        update={
            "evidence_id": "f" * 64,
            "period": "2022",
            "source_text": text,
            "value": Decimal(value),
            "unit": "dimensionless",
        }
    )
    with pytest.raises(FinsightError, match="calculation_validation_failed"):
        validator()(draft.model_copy(update={"operands": (draft.operands[0], b)}), packet, pages)
