"""Retained source intervals are distinct from full retrieved chunks."""

from .base import Contract, NonBlank, NonnegativeInt, PageIndex, Sha256
from .documents import SourceMetadata, SourceSpan
from .retrieval import Score


class EvidenceSlice(Contract):
    evidence_id: Sha256
    chunk_id: NonBlank
    document_id: NonBlank
    page_index: PageIndex
    source_spans: tuple[SourceSpan, ...]
    text: NonBlank
    source: SourceMetadata
    score: Score
    diagnostics: tuple[str, ...] = ()


class EvidencePacket(Contract):
    slices: tuple[EvidenceSlice, ...] = ()
    token_count: NonnegativeInt = 0
    dropped_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
