"""Scoring must not confuse units, pick convenient numbers or invent faithfulness."""

import importlib.util
from decimal import Decimal

import pytest

from finsight.contracts import Answer


def scoring():
    assert importlib.util.find_spec("finsight.evaluation.scoring"), "Missing financial scorer"
    from finsight.evaluation import scoring

    return scoring


@pytest.mark.parametrize(
    "text,value,unit",
    [
        ("$1.2 billion", "1200000000", "USD"),
        ("1,200 USD millions", "1200000000", "USD"),
        ("($25 million)", "-25000000", "USD"),
        ("-$25 million", "-25000000", "USD"),
        ("$-25 million", "-25000000", "USD"),
        ("$(25 million)", "-25000000", "USD"),
        ("−25 million EUR", "-25000000", "EUR"),
        ("5%", "0.05", "fraction"),
        ("0.05 ratio", "0.05", "fraction"),
        ("5 percentage points", "5", "percentage_point"),
        ("100 basis points", "1", "percentage_point"),
    ],
)
def test_financial_quantity_retains_sign_scale_and_dimension(text, value, unit):
    module = scoring()
    quantity = module.parse_quantity(text)
    assert quantity is not None
    assert quantity.value == Decimal(value) and quantity.unit == unit


@pytest.mark.parametrize(
    "text", ["1,2 million", "NaN", "infinity", "(25", "--25", "25 USD EUR", "1e999"]
)
def test_ambiguous_or_nonfinite_literals_are_not_guessed(text):
    assert scoring().parse_quantity(text) is None


def evaluated_answer(evidence_data, text, status="answered"):
    return Answer(
        status=status,
        answer_text=text,
        citations=(evidence_data,),
        limitations=("Incomplete.",) if status == "partial" else (),
    )


@pytest.mark.parametrize(
    "reference,text,expected",
    [
        ("$1.2 billion", "Revenue was $1,200 million in 2022. [1]", True),
        ("$1.2 billion", "Revenue was $1.3 billion in 2022. [1]", False),
        ("$25 million", "The loss was ($25 million) in 2022.", False),
        ("5%", "The increase was 5 percentage points.", False),
        ("5%", "The ratio was 0.05 ratio.", True),
        ("$1.2 billion", "Revenue was EUR 1.2 billion.", False),
        ("$1.2 billion", "Revenue was $2 billion and earnings were $1.2 billion.", None),
        ("$1.2 billion", "Revenue was $1.2 billion in 2021.", None),
        ("5%", "The ratio was 0.05.", None),
        ("$25 million", "The loss was -$25 million.", False),
        ("$25 million", "The amount was --25 million USD.", None),
        ("$25 million", "The amount was --$25 million.", None),
        ("$25", "The amount was $25 trillion.", None),
        ("$25 million", "The amount was USD 25 million per share.", None),
        ("$25 million", "The amount was $25 million/share.", None),
        ("25", "The amount was 25 rubles.", None),
        ("$25 million", "Revenue was not $25 million.", None),
        ("$25 million", "Revenue was more than $25 million.", None),
        ("$25 million", "Revenue was $25 million plus 5 rubles.", None),
        ("$100 million", "Revenue was $2022 million and earnings were $100 million.", None),
        ("$100 million", "Revenue was $2022.", False),
        ("$100 million", "Revenue was $2021 million.", False),
    ],
)
def test_numeric_comparison_is_conservative(reference, text, expected, evidence_data):
    result = scoring().score_answer(
        evaluated_answer(evidence_data, text), reference, question="Revenue in 2022?"
    )
    assert result["match"] is expected
    assert result["claim_faithfulness"] is None


@pytest.mark.parametrize(
    "question,text,period,expected",
    [
        ("Revenue in 2022?", "Revenue in FY2021 was $100 million.", None, None),
        ("Revenue in 2022?", "Revenue in Q1 2022 was $100 million.", None, None),
        ("Revenue in 2022?", "Revenue in FY2022 was $100 million.", None, True),
        ("Revenue in 2022?", "Revenue in FY'21 was $100 million.", None, None),
        ("Revenue in 2022 versus 2021?", "2021 revenue was $100 million.", None, None),
        ("Revenue?", "Revenue in 2021 was $100 million.", "2022", None),
        ("Revenue in 2021?", "Revenue in 2021 was $100 million.", "2022", True),
        ("Revenue in Q1 2022?", "Q2 2022 revenue was $100 million.", None, None),
        ("Revenue in Q1 2022?", "Q1 2022 revenue was $100 million.", None, True),
        ("Revenue in 2022?", "First quarter 2022 revenue was $100 million.", None, None),
    ],
)
def test_explicit_period_markers_cannot_disappear(question, text, period, expected, evidence_data):
    result = scoring().score_answer(
        evaluated_answer(evidence_data, text), "$100 million", question=question, period=period
    )
    assert result["match"] is expected


def test_partial_complex_error_and_abstention_are_distinct(evidence_data):
    module = scoring()
    assert (
        module.score_answer(evaluated_answer(evidence_data, "$100", "partial"), "$100")["match"]
        is None
    )
    assert (
        module.score_answer(evaluated_answer(evidence_data, "Yes, because earnings grew."), "Yes")[
            "match"
        ]
        is None
    )
    abstention = Answer(status="insufficient_evidence", limitations=("Missing source.",))
    assert module.score_answer(abstention, "$100")["match"] is False
    assert module.score_answer(evaluated_answer(evidence_data, "yes"), "Yes")["match"] is True
