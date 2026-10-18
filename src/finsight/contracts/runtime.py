"""Versioned baseline settings without credentials or provider dependencies."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import Contract, NonBlank, PositiveInt, Sha256, fingerprint

Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


class BaselineConfig(Contract):
    schema_version: Literal["1"] = "1"
    scenario: Literal["fixed_dense_v1"] = "fixed_dense_v1"
    source_fingerprint: Sha256 = "7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3"
    chunk_tokens: Annotated[int, Field(strict=True, ge=1, le=400)] = 400
    overlap_tokens: Annotated[int, Field(strict=True, ge=0, le=60)] = 60
    tokenizer_model: NonBlank = "Qwen/Qwen3-Embedding-8B"
    tokenizer_revision: NonBlank = "1d8ad4ca9b3dd8059ad90a75d4983776a23d44af"
    embedding_model: NonBlank = "Qwen/Qwen3-Embedding-8B"
    embedding_revision: NonBlank | None = None
    embedding_dimension: PositiveInt = 4096
    query_instruction: NonBlank = (
        "Given a financial question, retrieve passages from company filings "
        "that answer the question."
    )
    normalize_embeddings: Literal[True] = True
    metric: Literal["cosine"] = "cosine"
    generation_model: NonBlank = "claude-sonnet-5"
    prompt_version: NonBlank = "grounded-v1"
    effort: Literal["low"] = "low"
    thinking_type: Literal["adaptive"] = "adaptive"
    generation_service_tier: Literal["standard_only"] = "standard_only"
    candidate_count: Annotated[int, Field(strict=True, ge=1, le=15)] = 15
    top_k: Annotated[int, Field(strict=True, ge=1, le=15)] = 5
    context_tokens: Annotated[int, Field(strict=True, ge=1, le=3500)] = 3500
    question_tokens: Annotated[int, Field(strict=True, ge=1, le=512)] = 512
    input_tokens: Annotated[int, Field(strict=True, ge=1, le=6000)] = 6000
    output_tokens: Annotated[int, Field(strict=True, ge=1, le=1024)] = 1024
    attempt_timeout_s: Annotated[float, Field(gt=0, le=20)] = 20
    deadline_s: Annotated[float, Field(gt=0, le=45)] = 45
    budget_id: Literal["finsight-testing-2026-10-18"] = "finsight-testing-2026-10-18"
    ceiling_usd: Annotated[Decimal, Field(gt=0, le=5, allow_inf_nan=False)] = Decimal("5.00")
    working_usd: Annotated[Decimal, Field(gt=0, le=4, allow_inf_nan=False)] = Decimal("4.00")
    phase2_usd: Annotated[Decimal, Field(gt=0, le=Decimal("0.75"), allow_inf_nan=False)] = Decimal(
        "0.75"
    )

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if self.overlap_tokens >= self.chunk_tokens:
            raise ValueError("Overlap must be smaller than the chunk limit")
        if self.top_k > self.candidate_count:
            raise ValueError("Selection exceeds candidate count")
        if not self.phase2_usd <= self.working_usd < self.ceiling_usd:
            raise ValueError("Budget must preserve a reserve and bound Phase 2")
        return self

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class ProviderUsage(Contract):
    provider: Literal["nebius", "anthropic"]
    model: NonBlank
    input_tokens: Annotated[int, Field(strict=True, ge=0)] | None = None
    output_tokens: Annotated[int, Field(strict=True, ge=0)] | None = None
    cache_read_tokens: Annotated[int, Field(strict=True, ge=0)] | None = None
    cache_write_tokens: Annotated[int, Field(strict=True, ge=0)] | None = None
    cost_usd: Money | None = None
    cost_basis: Literal["provider_reported", "usage_priced", "unknown"] = "unknown"
    usage_known: bool = False
