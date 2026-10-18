"""Shared runtime and experiment contracts; never benchmark annotations."""

from .answers import Answer, AppError, Calculation, UsageMetrics
from .documents import Chunk, DocumentManifest, Page, SourceMetadata, SourceSpan, TextBlock
from .experiments import ExperimentConfig, ExperimentResult, QueryEvaluationRecord
from .ingestion import CorpusManifest, ExtractionConfig
from .retrieval import Evidence, QueryRequest, RetrievalCandidate, Score

__all__ = [
    "Answer",
    "AppError",
    "Calculation",
    "Chunk",
    "CorpusManifest",
    "DocumentManifest",
    "Evidence",
    "ExperimentConfig",
    "ExperimentResult",
    "ExtractionConfig",
    "Page",
    "QueryEvaluationRecord",
    "QueryRequest",
    "RetrievalCandidate",
    "Score",
    "SourceMetadata",
    "SourceSpan",
    "TextBlock",
    "UsageMetrics",
]
