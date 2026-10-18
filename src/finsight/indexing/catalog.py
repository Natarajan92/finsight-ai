"""Exact chunks and diagnostics bound to unchanged manifest and extracted pages."""

from finsight.chunking.diagnostics import chunk_diagnostics
from finsight.chunking.fixed import chunk_pages
from finsight.contracts import BaselineConfig
from finsight.contracts.base import fingerprint
from finsight.contracts.indexing import ChunkCatalog
from finsight.contracts.ingestion import CorpusManifest
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import OffsetTokenizer, PageRepository


def page_key(document_id: str, page_index: int) -> str:
    return f"{document_id}:{page_index}"


def create_catalog(
    corpus: CorpusManifest,
    pages: PageRepository,
    config: BaselineConfig,
    tokenizer: OffsetTokenizer,
) -> ChunkCatalog:
    if corpus.source_fingerprint != config.source_fingerprint:
        raise FinsightError("index_integrity")
    chunks = []
    page_hashes = {}
    diagnostics = {}
    parsers = set()
    for document in sorted(corpus.documents, key=lambda d: d.document_id):
        if hasattr(pages, "validate"):
            pages.validate(document.document_id)
        extracted = tuple(pages.get(document.document_id, i) for i in range(document.page_count))
        for page in extracted:
            page_hashes[page_key(page.document_id, page.page_index)] = fingerprint(
                page.model_dump(mode="json")
            )
            parsers.add(page.parser_version)
        generated = chunk_pages(document, extracted, config, tokenizer)
        for chunk in generated:
            diagnostics[chunk.chunk_id] = chunk_diagnostics(chunk, extracted[chunk.page_start])
        chunks.extend(generated)
    artifact = getattr(tokenizer, "artifact", None)
    tokenizer_id = (
        artifact.fingerprint()
        if artifact is not None
        else fingerprint({"injected_tokenizer": type(tokenizer).__name__})
    )
    extraction = getattr(pages, "extraction", None)
    payload = dict(
        manifest_fingerprint=fingerprint(corpus.model_dump(mode="json")),
        source_fingerprint=corpus.source_fingerprint,
        config_fingerprint=config.fingerprint(),
        extraction_fingerprint=fingerprint(
            {
                "parsers": sorted(parsers),
                "extraction": extraction.fingerprint() if extraction else "injected",
            }
        ),
        tokenizer_fingerprint=tokenizer_id,
        page_fingerprints=page_hashes,
        chunks=[c.model_dump(mode="json") for c in chunks],
        diagnostics=diagnostics,
    )
    # Include defaults in the fingerprint exactly as serialized.
    catalog = ChunkCatalog(**payload, payload_fingerprint="0" * 64)
    return catalog.model_copy(
        update={
            "payload_fingerprint": fingerprint(
                catalog.model_dump(mode="json", exclude={"payload_fingerprint"})
            )
        }
    )


def validate_catalog(
    catalog: ChunkCatalog,
    corpus: CorpusManifest,
    config: BaselineConfig,
    pages: PageRepository,
    tokenizer: OffsetTokenizer,
) -> None:
    if (
        catalog.payload_fingerprint
        != fingerprint(catalog.model_dump(mode="json", exclude={"payload_fingerprint"}))
        or catalog.manifest_fingerprint != fingerprint(corpus.model_dump(mode="json"))
        or catalog.source_fingerprint != corpus.source_fingerprint
        or config.source_fingerprint != corpus.source_fingerprint
        or catalog.config_fingerprint != config.fingerprint()
        or len(catalog.chunks_by_id) != len(catalog.chunks)
    ):
        raise FinsightError("index_integrity")
    # Self-consistent local hashes alone cannot establish complete corpus membership.
    if catalog != create_catalog(corpus, pages, config, tokenizer):
        raise FinsightError("index_integrity")
