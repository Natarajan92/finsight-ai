"""Source-only persisted identities. Completion is an atomic publication gate."""

from typing import Literal

from .base import Contract, NonBlank, NonnegativeInt, PositiveInt, Sha256, fingerprint
from .documents import Chunk


class ChunkCatalog(Contract):
    schema_version: Literal["1"] = "1"
    manifest_fingerprint: Sha256
    source_fingerprint: Sha256
    config_fingerprint: Sha256
    extraction_fingerprint: Sha256
    tokenizer_fingerprint: Sha256
    page_fingerprints: dict[str, Sha256]
    chunks: tuple[Chunk, ...]
    diagnostics: dict[str, tuple[str, ...]]
    payload_fingerprint: Sha256

    @property
    def chunks_by_id(self) -> dict[str, Chunk]:
        return {c.chunk_id: c for c in self.chunks}


class IndexManifest(Contract):
    schema_version: Literal["1"] = "1"
    complete: Literal[True] = True
    budget_id: NonBlank
    catalog_fingerprint: Sha256
    source_fingerprint: Sha256
    config_fingerprint: Sha256
    chunk_ids: tuple[Sha256, ...]
    chunk_count: NonnegativeInt
    dimension: PositiveInt
    metric: Literal["cosine"] = "cosine"
    provider: Literal["nebius"] = "nebius"
    model: NonBlank
    tokenizer_revision: NonBlank
    tokenizer_fingerprint: Sha256
    software: dict[str, str]
    vector_hashes: dict[str, Sha256]

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))
