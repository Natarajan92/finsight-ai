"""Explicit request scope and scores with unambiguous ordering."""

from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, model_validator

from .base import Contract, NonBlank, PageIndex, PositiveInt
from .documents import Chunk, SourceMetadata


class Score(Contract):
    kind: Literal["cosine_similarity", "cosine_distance", "rerank_logit"]
    direction: Literal["higher_is_better", "lower_is_better"]
    value: float

    @model_validator(mode="after")
    def consistent_direction(self) -> Self:
        expected = "lower_is_better" if self.kind == "cosine_distance" else "higher_is_better"
        if self.direction != expected:
            raise ValueError("Score direction does not match its kind")
        return self


class QueryRequest(Contract):
    question: NonBlank
    company: NonBlank | None = None
    document_ids: Annotated[tuple[NonBlank, ...], Field(min_length=1)] | None = None
    period: NonBlank | None = None
    chunk_strategy: Literal["fixed", "semantic"] = "fixed"
    retrieval_strategy: Literal["dense"] = "dense"
    rerank: StrictBool = False
    top_k: Annotated[int, Field(strict=True, ge=1, le=15)] = 5


class RetrievalCandidate(Contract):
    chunk: Chunk
    source: SourceMetadata
    rank: PositiveInt
    score: Score


class Evidence(Contract):
    """Evidence produced from retrieved PDF content, never a gold annotation."""

    chunk_id: NonBlank
    document_id: NonBlank
    page_index: PageIndex
    source_quote: NonBlank
    score: Score
    source: SourceMetadata
