"""Versioned experiment identities; legacy baseline fingerprints stay unchanged."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .base import Contract, fingerprint
from .runtime import BaselineConfig


class SemanticChunkConfig(Contract):
    algorithm: Literal["adjacent-nebius-v1"] = "adjacent-nebius-v1"
    unit_min_tokens: Annotated[int, Field(strict=True, ge=1, le=128)] = 64
    unit_max_tokens: Annotated[int, Field(strict=True, ge=1, le=128)] = 128
    minimum_new_tokens: Annotated[int, Field(strict=True, ge=1, le=400)] = 64
    percentile: Annotated[float, Field(gt=0, le=100)] = 95

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.unit_min_tokens > self.unit_max_tokens:
            raise ValueError("Minimum unit size exceeds maximum")
        return self


class SemanticIndexConfig(BaselineConfig):
    scenario: Literal["semantic_dense_v1"] = "semantic_dense_v1"
    chunk_strategy: Literal["semantic"] = "semantic"
    semantic: SemanticChunkConfig = Field(default_factory=SemanticChunkConfig)

    @model_validator(mode="after")
    def semantic_bounds(self) -> Self:
        if self.semantic.minimum_new_tokens > self.chunk_tokens:
            raise ValueError("Minimum new tokens exceed chunk size")
        return self


class RerankerConfig(Contract):
    model: Literal["cross-encoder/ms-marco-MiniLM-L6-v2"] = "cross-encoder/ms-marco-MiniLM-L6-v2"
    revision: Literal["eeed17e3bfc6fa06a790f2d12a9501fec587fccf"] = (
        "eeed17e3bfc6fa06a790f2d12a9501fec587fccf"
    )
    model_file: Literal["onnx/model.onnx"] = "onnx/model.onnx"
    model_sha256: Literal["5d3e70fd0c9ff14b9b5169a51e957b7a9c74897afd0a35ce4bd318150c1d4d4a"] = (
        "5d3e70fd0c9ff14b9b5169a51e957b7a9c74897afd0a35ce4bd318150c1d4d4a"
    )
    provider: Literal["CPUExecutionProvider"] = "CPUExecutionProvider"
    maximum_tokens: Literal[512] = 512
    window_overlap: Annotated[int, Field(strict=True, ge=0, le=128)] = 64
    batch_size: Annotated[int, Field(strict=True, ge=1, le=4)] = 4
    threads: Literal[1] = 1


class RetrievalExperimentConfig(Contract):
    schema_version: Literal["1"] = "1"
    arm: Literal["A", "B", "C", "D"] = "A"
    baseline: BaselineConfig = Field(default_factory=BaselineConfig)
    semantic: SemanticChunkConfig = Field(default_factory=SemanticChunkConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    phase3_usd: Annotated[Decimal, Field(gt=0, le=Decimal("0.75"), allow_inf_nan=False)] = Decimal(
        "0.75"
    )

    @property
    def chunk_strategy(self) -> Literal["fixed", "semantic"]:
        return "semantic" if self.arm in {"B", "D"} else "fixed"

    @property
    def rerank(self) -> bool:
        return self.arm in {"C", "D"}

    def index_config(self) -> BaselineConfig:
        if self.chunk_strategy == "fixed":
            return self.baseline
        values = self.baseline.model_dump()
        values["scenario"] = "semantic_dense_v1"
        return SemanticIndexConfig(**values, semantic=self.semantic)

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))
