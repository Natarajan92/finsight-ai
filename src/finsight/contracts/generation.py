"""Untrusted model drafts contain references, never authoritative source metadata."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .answers import FiniteDecimal
from .base import Contract, NonBlank, Sha256


class DraftReference(Contract):
    evidence_id: NonBlank
    quote: NonBlank


class DraftClaim(Contract):
    text: NonBlank
    references: Annotated[tuple[DraftReference, ...], Field(min_length=1)]


class DraftOperand(Contract):
    name: NonBlank
    evidence_id: NonBlank
    source_text: NonBlank
    value: FiniteDecimal
    unit: NonBlank
    period: NonBlank


class DraftCalculation(Contract):
    operator: Literal["add", "subtract", "multiply", "divide"]
    operands: Annotated[tuple[DraftOperand, ...], Field(min_length=2, max_length=2)]
    result: FiniteDecimal
    unit: NonBlank


class DraftAnswer(Contract):
    status: Literal["answered", "partial", "insufficient_evidence"]
    claims: tuple[DraftClaim, ...] = ()
    limitations: tuple[NonBlank, ...] = ()
    calculation: DraftCalculation | None = None

    @model_validator(mode="after")
    def grounded_shape(self) -> Self:
        if self.status == "insufficient_evidence":
            if self.claims or self.calculation is not None:
                raise ValueError("Abstention cannot contain model claims/calculation")
        elif not self.claims:
            raise ValueError("Answered drafts require claims")
        if self.status == "partial" and not self.limitations:
            raise ValueError("Partial draft requires limitations")
        return self


class GroundedPrompt(Contract):
    system: NonBlank
    user: NonBlank
    output_schema: dict[str, object] = Field(alias="schema")
    fingerprint: Sha256

    @property
    def schema(self) -> dict[str, object]:
        return self.output_schema
