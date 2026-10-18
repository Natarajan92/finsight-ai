"""Document identity and per-page extraction provenance."""

from itertools import pairwise
from typing import Literal, Self

from pydantic import HttpUrl, model_validator

from .base import Contract, NonBlank, NonnegativeInt, PageIndex, PositiveInt, Sha256


class SourceMetadata(Contract):
    doc_name: NonBlank
    company: NonBlank | None
    fiscal_period: NonBlank | None
    filing_type: NonBlank | None
    source_url: HttpUrl | None
    local_path: NonBlank
    sha256: Sha256


class DocumentManifest(SourceMetadata):
    document_id: NonBlank
    page_count: PositiveInt
    ingestion_version: NonBlank


class Page(Contract):
    document_id: NonBlank
    page_index: PageIndex
    text: str
    extraction_status: Literal["ok", "empty", "error"]
    parser_version: NonBlank
    table_diagnostics: tuple[NonBlank, ...] = ()


class SourceSpan(Contract):
    """Half-open character offsets into one unchanged extracted PDF page."""

    page_index: PageIndex
    char_start: NonnegativeInt
    char_end: PositiveInt

    @model_validator(mode="after")
    def ordered_offsets(self) -> Self:
        if self.char_end <= self.char_start:
            raise ValueError("Source span must have char_end > char_start")
        return self


class Chunk(Contract):
    chunk_id: NonBlank
    document_id: NonBlank
    page_start: PageIndex
    page_end: PageIndex
    source_spans: tuple[SourceSpan, ...]
    chunk_strategy: Literal["fixed", "semantic"]
    config_fingerprint: Sha256
    content: NonBlank
    token_count: NonnegativeInt
    section_title: NonBlank | None = None
    content_type: Literal["text", "table", "mixed"] = "text"

    @model_validator(mode="after")
    def consistent_provenance(self) -> Self:
        if not self.source_spans:
            raise ValueError("A chunk requires source spans")
        if (self.page_start, self.page_end) != (
            self.source_spans[0].page_index,
            self.source_spans[-1].page_index,
        ):
            raise ValueError("Chunk page bounds must match its ordered source spans")
        for previous, current in pairwise(self.source_spans):
            if current.page_index < previous.page_index or (
                current.page_index == previous.page_index and current.char_start < previous.char_end
            ):
                raise ValueError("Source spans must be ordered and nonoverlapping")
        return self
