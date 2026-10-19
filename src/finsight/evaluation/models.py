"""Offline evaluation records, including private reference/review material."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from finsight.contracts import Answer, UsageMetrics
from finsight.contracts.base import Contract, NonBlank, NonnegativeInt, Sha256
from finsight.contracts.retrieval_experiments import RetrievalExperimentConfig


class EvaluationConfig(Contract):
    arms: tuple[Literal["A", "B", "C", "D"], ...] = ("A",)
    max_cost_usd: Annotated[Decimal, Field(gt=0, le=Decimal("0.25"), allow_inf_nan=False)] = (
        Decimal("0.25")
    )
    scorer_version: Literal["financial-match-v1"] = "financial-match-v1"

    @model_validator(mode="after")
    def unique_arms(self) -> Self:
        if not self.arms or len(set(self.arms)) != len(self.arms):
            raise ValueError("Select unique arms")
        return self


class ReviewClaim(Contract):
    index: Annotated[int, Field(gt=0)]
    text: NonBlank
    fingerprint: Sha256


class EvaluationRecord(Contract):
    question_id: NonBlank
    arm: Literal["A", "B", "C", "D"]
    question: NonBlank
    reference: NonBlank
    status: Literal["answered", "partial", "insufficient_evidence", "error"]
    answer: Answer
    trace_id: NonBlank
    trace_fingerprint: Sha256
    runtime_config_fingerprint: Sha256 | None = None
    index_fingerprint: Sha256 | None = None
    dense_pool_fingerprint: Sha256 | None = None
    metrics: dict[str, float | None]
    match: dict[str, str | bool | None]
    claims: tuple[ReviewClaim, ...] = ()
    replay: bool = False

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        if self.status != self.answer.status or [c.index for c in self.claims] != list(
            range(1, len(self.claims) + 1)
        ):
            raise ValueError("Result status or claim identity changed")
        if (
            set(self.match) != {"match", "method", "reason", "claim_faithfulness"}
            or (self.match["match"] is not None and type(self.match["match"]) is not bool)
            or self.match["claim_faithfulness"] is not None
        ):
            raise ValueError("Automatic scoring cannot supply semantic faithfulness")
        return self


class EvaluationRun(Contract):
    schema_version: Literal["1"] = "1"
    config: EvaluationConfig
    identity: Sha256
    source_fingerprint: Sha256
    dataset_fingerprint: Sha256
    split_fingerprint: Sha256
    runtime_configs: dict[str, dict] = Field(default_factory=dict)
    runtime_config_fingerprints: dict[str, Sha256] = Field(default_factory=dict)
    index_fingerprints: dict[str, Sha256] = Field(default_factory=dict)
    software: dict[str, str] = Field(default_factory=dict)
    question_ids: tuple[NonBlank, ...]
    expected_records: NonnegativeInt
    records: tuple[EvaluationRecord, ...]
    complete: bool
    replay: bool = False
    new_cost_usd: Decimal | None = None
    new_reservation_usd: Decimal | None = None
    ledger_accounted_delta_usd: Decimal | None = None
    safety: tuple[dict[str, str | bool | int], ...] = ()
    original_usage: UsageMetrics = Field(default_factory=UsageMetrics)

    @model_validator(mode="after")
    def consistent_records(self) -> Self:
        if not self.question_ids or len(set(self.question_ids)) != len(self.question_ids):
            raise ValueError("Evaluation requires unique nonempty question IDs")
        if self.runtime_configs:
            if any(
                set(values) != set(self.config.arms)
                for values in (
                    self.runtime_configs,
                    self.runtime_config_fingerprints,
                    self.index_fingerprints,
                )
            ):
                raise ValueError("Runtime configuration membership changed")
            for arm, raw in self.runtime_configs.items():
                runtime = RetrievalExperimentConfig.model_validate(raw)
                if (
                    runtime.arm != arm
                    or runtime.fingerprint() != self.runtime_config_fingerprints[arm]
                    or (runtime.baseline.source_fingerprint != self.source_fingerprint)
                ):
                    raise ValueError("Runtime configuration fingerprint changed")
            if any(
                r.runtime_config_fingerprint != self.runtime_config_fingerprints[r.arm]
                or r.index_fingerprint != self.index_fingerprints[r.arm]
                for r in self.records
            ):
                raise ValueError("Evaluated runtime differs from declared configuration")
        keys = [(r.question_id, r.arm) for r in self.records]
        if len(keys) != len(set(keys)) or any(
            r.question_id not in self.question_ids or r.arm not in self.config.arms
            for r in self.records
        ):
            raise ValueError("Duplicate or undeclared evaluated case")
        if self.expected_records != len(self.question_ids) * len(self.config.arms):
            raise ValueError("Evaluation denominator changed")
        if self.complete and (
            len(self.records) != self.expected_records
            or any(r.status == "error" for r in self.records)
            or not self.safety
            or not all(r["passed"] is True for r in self.safety)
        ):
            raise ValueError("Incomplete execution cannot be reported complete")
        return self
