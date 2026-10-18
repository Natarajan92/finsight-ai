"""Shared runtime and experiment contracts; never benchmark annotations."""

from .answers import Answer, AppError, Calculation, UsageMetrics
from .documents import Chunk, DocumentManifest, Page, SourceMetadata, SourceSpan, TextBlock
from .experiments import ExperimentConfig, ExperimentResult, QueryEvaluationRecord
from .ingestion import CorpusManifest, ExtractionConfig
from .retrieval import Evidence, QueryRequest, RetrievalCandidate, Score
from .runtime import BaselineConfig, ProviderUsage
from .tracing import ProviderAttempt, RunTrace

__all__ = [
    "Answer",
    "BaselineConfig",
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
    "ProviderAttempt",
    "ProviderUsage",
    "QueryEvaluationRecord",
    "QueryRequest",
    "RetrievalCandidate",
    "Score",
    "RunTrace",
    "SourceMetadata",
    "SourceSpan",
    "TextBlock",
    "UsageMetrics",
]
