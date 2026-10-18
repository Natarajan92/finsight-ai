"""Shared runtime and experiment contracts; never benchmark annotations."""

from .answers import Answer, AppError, Calculation, UsageMetrics
from .documents import Chunk, DocumentManifest, Page, SourceMetadata, SourceSpan
from .experiments import ExperimentConfig, ExperimentResult, QueryEvaluationRecord
from .retrieval import Evidence, QueryRequest, RetrievalCandidate, Score

__all__ = [
    "Answer",
    "AppError",
    "Calculation",
    "Chunk",
    "DocumentManifest",
    "Evidence",
    "ExperimentConfig",
    "ExperimentResult",
    "Page",
    "QueryEvaluationRecord",
    "QueryRequest",
    "RetrievalCandidate",
    "Score",
    "SourceMetadata",
    "SourceSpan",
    "UsageMetrics",
]
