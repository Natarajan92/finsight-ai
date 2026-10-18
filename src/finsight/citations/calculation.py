"""Two cited operands, strict literals and bounded exact Decimal operations."""

import re
from decimal import Decimal, DecimalException, Inexact, localcontext

from finsight.contracts import Calculation, QueryRequest
from finsight.contracts.context import EvidencePacket
from finsight.contracts.generation import DraftCalculation
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import PageRepository

from .validation import packet_map, source_fragments

UNSIGNED = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
LITERAL = rf"(?:\({UNSIGNED}\)|[-+−]?{UNSIGNED})"
OCCURRENCE = re.compile(rf"(?<![\w.,(+−-]){LITERAL}(?![\w.,)])")
COMPARISON = re.compile(
    r"\b(?:compare|comparison|change|difference|growth|increase|decrease|"
    r"versus|vs|from|ratio)\b|year[- ]over[- ]year",
    re.IGNORECASE,
)


def parse_financial_literal(text: str) -> Decimal:
    if len(text) > 64 or re.fullmatch(LITERAL, text) is None:
        raise FinsightError("calculation_validation_failed")
    value = Decimal(text.replace(",", "").replace("−", "-").strip("()"))
    if text.startswith("("):
        value = -value
    if not value.is_finite() or abs(value) > Decimal("1e18") or value.as_tuple().exponent < -18:
        raise FinsightError("calculation_validation_failed")
    return value


def _unit(unit: str) -> str:
    normalized = " ".join(unit.casefold().split())
    return "dimensionless" if normalized in {"dimensionless", "ratio"} else normalized


def _unit_in_source(unit: str, text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    if unit == "dimensionless":
        return bool(re.search(r"\b(?:dimensionless|ratio|factor)\b", normalized))
    if not re.search(r"(?<!\w)" + re.escape(unit) + r"(?!\w)", normalized):
        return False
    if re.fullmatch(r"(?:usd|eur|gbp|jpy|cad)", unit) and re.search(
        r"\b(?:thousand|million|billion)s?\b", normalized
    ):
        return False  # A declared currency cannot silently discard a supplied scale.
    return True


def _comparison_allowed(periods: set[str], request: QueryRequest | None) -> bool:
    if len(periods) <= 1:
        return True
    if request is None or not COMPARISON.search(request.question):
        return False
    return all(
        re.search(r"(?<!\d)" + re.escape(period) + r"(?!\d)", request.question)
        for period in periods
    )


def validate_calculation(
    calculation: DraftCalculation,
    packet: EvidencePacket,
    pages: PageRepository,
    *,
    request: QueryRequest | None = None,
) -> Calculation:
    try:
        calculation = DraftCalculation.model_validate(calculation.model_dump(mode="json"))
        items = packet_map(packet)
        values = []
        units = []
        names = []
        periods = set()
        for operand in calculation.operands:
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", operand.name) is None:
                raise ValueError("Unsupported operand name")
            item = items.get(operand.evidence_id)
            if item is None:
                raise ValueError("Unsupplied operand source")
            fragments = source_fragments(item, pages)
            value = parse_financial_literal(operand.source_text)
            unit = _unit(operand.unit)
            if value != operand.value or not any(
                operand.source_text in [m.group() for m in OCCURRENCE.finditer(part)]
                and _unit_in_source(unit, part)
                and re.search(r"(?<!\w)" + re.escape(operand.period) + r"(?!\w)", part)
                for part in fragments
            ):
                raise ValueError("Numeric literal, scale or period is not in its supplied span")
            values.append(value)
            units.append(unit)
            names.append(operand.name)
            periods.add(operand.period)
        if len(set(names)) != 2 or not _comparison_allowed(periods, request):
            raise ValueError("Duplicate operand or unrequested cross-period calculation")
        a, b = values
        left, right = units
        operator = calculation.operator
        with localcontext() as context:
            context.prec = 28
            context.Emax = 24
            context.Emin = -24
            context.traps[Inexact] = True
            if operator in {"add", "subtract"}:
                if left != right:
                    raise ValueError("Incompatible units")
                result = a + b if operator == "add" else a - b
                result_unit = left
                symbol = "+" if operator == "add" else "-"
            elif operator == "multiply":
                if "dimensionless" not in units:
                    raise ValueError("Unsupported product units")
                result = a * b
                result_unit = right if left == "dimensionless" else left
                symbol = "*"
            else:
                if b == 0 or (right != "dimensionless" and left != right):
                    raise ValueError("Unsupported division")
                result = a / b
                result_unit = "dimensionless" if left == right else left
                symbol = "/"
        if (
            not result.is_finite()
            or abs(result) > Decimal("1e24")
            or result != calculation.result
            or _unit(calculation.unit) != result_unit
        ):
            raise ValueError("Declared result or unit differs")
        return Calculation(
            expression=f"{names[0]} {symbol} {names[1]}",
            operands=dict(zip(names, values, strict=True)),
            result=result,
            unit=calculation.unit,
        )
    except (ValueError, TypeError, DecimalException, FinsightError):
        raise FinsightError("calculation_validation_failed") from None
