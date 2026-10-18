"""Structured outcomes; semantic support is verified by later pipeline stages."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, model_validator

from .base import Contract, NonBlank, NonnegativeFloat, NonnegativeInt
from .retrieval import Evidence

FiniteDecimal = Annotated[Decimal, Field(allow_inf_nan=False)]


class UsageMetrics(Contract):
    input_tokens: NonnegativeInt | None = None
    output_tokens: NonnegativeInt | None = None
    model_calls: NonnegativeInt | None = None
    embeddings: NonnegativeInt | None = None
    latency_ms: NonnegativeFloat | None = None
    cost_usd: Annotated[Decimal, Field(ge=0, allow_inf_nan=False)] | None = None


class AppError(Contract):
    code: NonBlank
    message: NonBlank
    retryable: StrictBool = False


class Calculation(Contract):
    expression: NonBlank
    operands: dict[NonBlank, FiniteDecimal]
    result: FiniteDecimal
    unit: NonBlank


class Answer(Contract):
    status: Literal["answered", "partial", "insufficient_evidence", "error"]
    answer_text: str = ""
    citations: tuple[Evidence, ...] = ()
    limitations: tuple[NonBlank, ...] = ()
    calculation: Calculation | None = None
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    error: AppError | None = None

    @model_validator(mode="after")
    def consistent_status(self) -> Self:
        if self.status in {"answered", "partial"}:
            if not self.answer_text.strip() or not self.citations:
                raise ValueError("Answered and partial results require text and citations")
        elif self.citations or self.calculation is not None:
            raise ValueError("Failure/abstention results cannot carry citations or calculations")
        if self.status == "partial" and not self.limitations:
            raise ValueError("Partial results must describe their limitations")
        if (self.status == "error") != (self.error is not None):
            raise ValueError("Only error results require structured error details")
        return self
