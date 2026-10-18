"""Experiment configuration and measured output, without benchmark gold."""

import hashlib
import json
from typing import Literal, Self

from pydantic import Field, StrictBool, model_validator

from .answers import Answer, UsageMetrics
from .base import Contract, NonBlank, NonnegativeInt, PositiveInt, Sha256
from .retrieval import RetrievalCandidate


class ExperimentConfig(Contract):
    chunk_strategy: Literal["fixed", "semantic"] = "fixed"
    rerank: StrictBool = False
    candidate_count: PositiveInt = 15
    top_k: PositiveInt = 5
    context_token_budget: PositiveInt = 3500
    seed: NonnegativeInt = 0
    embedding_model: NonBlank | None = None
    embedding_revision: NonBlank | None = None
    embedding_dimension: PositiveInt | None = None
    generation_model: NonBlank | None = None
    prompt_version: NonBlank | None = None

    @model_validator(mode="after")
    def bounded_selection(self) -> Self:
        if self.top_k > self.candidate_count:
            raise ValueError("top_k cannot exceed the pre-rank candidate count")
        return self

    def fingerprint(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class QueryEvaluationRecord(Contract):
    question_id: NonBlank
    retrieved: tuple[RetrievalCandidate, ...] = ()
    answer: Answer | None = None
    metrics: dict[NonBlank, float | None] = Field(default_factory=dict)


class ExperimentResult(Contract):
    config: ExperimentConfig
    config_fingerprint: Sha256
    source_fingerprint: Sha256
    dataset_fingerprint: Sha256
    split_fingerprint: Sha256
    records: tuple[QueryEvaluationRecord, ...] = ()
    aggregate_metrics: dict[NonBlank, float | None] = Field(default_factory=dict)
    usage: UsageMetrics = Field(default_factory=UsageMetrics)

    @model_validator(mode="after")
    def matching_config(self) -> Self:
        if self.config_fingerprint != self.config.fingerprint():
            raise ValueError("Config fingerprint does not match the recorded configuration")
        return self
