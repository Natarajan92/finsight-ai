"""Conservative finite financial quantities; no unit or period inference."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, localcontext

NUMBER = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
CURRENCY = {"$": "USD", "usd": "USD", "€": "EUR", "eur": "EUR", "£": "GBP", "gbp": "GBP"}
SCALES = {
    "thousand": Decimal("1000"),
    "k": Decimal("1000"),
    "million": Decimal("1000000"),
    "m": Decimal("1000000"),
    "billion": Decimal("1000000000"),
    "bn": Decimal("1000000000"),
}
UNIT = (
    r"(?:usd|eur|gbp|[$€£]|thousands?|millions?|billions?|bn|k|m|"
    r"percentage\s+points?|basis\s+points?|percent(?:age)?|%|ratio|dimensionless)"
)
OCCURRENCE = re.compile(
    rf"(?<![\w.,+\-($€£])\(?[+-]?\s*(?:(?:USD|EUR|GBP|[$€£])\s*)?\(?{NUMBER}"
    rf"(?:\s*{UNIT}){{0,3}}\)?(?![\w,]|\.\d)",
    re.I,
)


@dataclass(frozen=True)
class Quantity:
    value: Decimal
    unit: str


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("−", "-")
    text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", text)
    return " ".join(text.casefold().split()).rstrip(".")


def parse_quantity(text: str) -> Quantity | None:
    if len(text) > 256:
        return None
    text = normalize_text(text).strip()
    currency = None
    outer_sign = ""
    if text.startswith(("-", "+")):
        outer_sign, text = text[0], text[1:].strip()
    # Permit both ($25) and $(25), with one accounting sign only.
    match = re.match(r"^(usd|eur|gbp|[$€£])\s*", text)
    if match:
        currency, text = CURRENCY[match[1]], text[match.end() :]
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    elif "(" in text or ")" in text:
        return None
    match = re.match(r"^(usd|eur|gbp|[$€£])\s*", text)
    if match:
        if currency:
            return None
        currency, text = CURRENCY[match[1]], text[match.end() :]
    number = re.match(NUMBER, text)
    if (
        not number
        or len(number[0]) > 40
        or (outer_sign and negative)
        or ((negative or outer_sign) and number[0].startswith(("-", "+")))
    ):
        return None
    rest = text[number.end() :].strip()
    rest = re.sub(r"\bpercentage points?\b", "percentage_point", rest)
    rest = re.sub(r"\bbasis points?\b", "basis_point", rest)
    rest = re.sub(r"\b(thousand|million|billion)s\b", r"\1", rest)
    rest = rest.replace("%", " % ")
    tokens = rest.split()
    scales = [t for t in tokens if t in SCALES]
    currencies = [t for t in tokens if t in CURRENCY]
    dimensions = [
        t
        for t in tokens
        if t
        in {
            "%",
            "percent",
            "percentage",
            "ratio",
            "dimensionless",
            "percentage_point",
            "basis_point",
        }
    ]
    if (
        len(scales) > 1
        or len(currencies) + bool(currency) > 1
        or len(dimensions) > 1
        or len(tokens) != len(scales) + len(currencies) + len(dimensions)
        or ((currency or currencies) and dimensions)
        or (scales and dimensions)
    ):
        return None
    with localcontext() as context:
        context.prec = 60
        value = Decimal(number[0].replace(",", "")) * (-1 if negative or outer_sign == "-" else 1)
        if scales:
            value *= SCALES[scales[0]]
        unit = currency or (CURRENCY[currencies[0]] if currencies else "number")
        if dimensions:
            dimension = dimensions[0]
            if dimension in {"%", "percent", "percentage"}:
                value /= 100
            if dimension == "basis_point":
                value /= 100
            unit = (
                "percentage_point"
                if dimension in {"basis_point", "percentage_point"}
                else "fraction"
            )
    if not value.is_finite() or abs(value) > Decimal("1e24") or value.as_tuple().exponent < -24:
        return None
    return Quantity(value, unit)


def quantities(text: str) -> tuple[Quantity, ...]:
    text = unicodedata.normalize("NFKC", text).replace("−", "-")
    text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", text)
    found, covered = [], list(text)
    for match in OCCURRENCE.finditer(text):
        quantity = parse_quantity(match[0])
        tail = text[match.end() :].lstrip()
        # A recognized prefix is insufficient: unknown magnitudes, currencies,
        # share denominators and malformed signs must not become scalar matches.
        following = re.match(r"[A-Za-z]+|[/+%$€£()\-]", tail)
        connectors = {"in", "for", "of", "as", "at", "on", "and", "or", "from", "to", "was", "is"}
        if quantity is None or (following and following[0].casefold() not in connectors):
            return ()
        found.append(quantity)
        covered[match.start() : match.end()] = " " * (match.end() - match.start())
    # Never select a convenient valid number beside a malformed numeric fragment.
    if re.search(r"\d", "".join(covered)):
        return ()
    return tuple(found)
