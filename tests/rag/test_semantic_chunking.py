"""Semantic vectors must affect boundaries without altering source characters."""

import importlib
from decimal import Decimal

import pytest

from finsight.contracts.retrieval_experiments import SemanticChunkConfig, SemanticIndexConfig
from finsight.indexing.embedding_cache import EmbeddingCache
from finsight.runtime.errors import FinsightError


def semantic_module():
    assert importlib.util.find_spec("finsight.chunking.semantic"), "Missing semantic chunker"
    return importlib.import_module("finsight.chunking.semantic")


@pytest.fixture
def semantic_source(page_factory, char_tokenizer, tmp_path):
    module = semantic_module()
    doc, page = page_factory(
        "A" * 100 + "\n\n" + "B" * 100 + "\n\n" + "C" * 100 + "\n\n" + "D" * 100
    )
    config = SemanticIndexConfig(embedding_dimension=3, chunk_tokens=220, overlap_tokens=20)
    units = module.semantic_units(doc, (page,), config, char_tokenizer)
    cache = EmbeddingCache(tmp_path / "emb", config)
    return module, doc, (page,), config, char_tokenizer, units, cache, tmp_path / "semantic"


def put_vectors(units, cache, vectors):
    for unit, vector in zip(units, vectors, strict=True):
        cache.put(cache.record(unit.text, "document", vector))


def test_semantic_vectors_change_boundaries_and_preserve_exact_coverage(semantic_source):
    module, doc, pages, config, tokenizer, units, cache, root = semantic_source
    assert len(units) == 4
    put_vectors(units, cache, [[1, 0, 0]] * 2 + [[-1, 0, 0]] * 2)
    preparation = module.prepare_semantics(doc, pages, config, tokenizer, cache, root)
    chunks = module.semantic_chunk_pages(doc, pages, config, tokenizer, preparation)
    assert chunks[0].source_spans[0].char_end == 204  # Topic change after the second unit.
    assert preparation.threshold == 2
    assert any(d.reason == "semantic" for d in preparation.decisions)
    covered = set()
    for chunk in chunks:
        span = chunk.source_spans[0]
        assert chunk.content == pages[0].text[span.char_start : span.char_end]
        assert chunk.token_count <= 220 and chunk.chunk_strategy == "semantic"
        covered.update(range(span.char_start, span.char_end))
    assert covered == set(range(len(pages[0].text)))
    put_vectors(units, cache, [[1, 0, 0]] * 4)
    with pytest.raises(FinsightError, match="semantic_preparation_integrity"):
        module.load_preparation(doc, pages, config, tokenizer, cache, root)
    other_root = root / "flat"
    flat = module.prepare_semantics(doc, pages, config, tokenizer, cache, other_root)
    flat_chunks = module.semantic_chunk_pages(doc, pages, config, tokenizer, flat)
    assert flat.threshold is None
    assert flat_chunks[0].source_spans[0].char_end == 220


def test_missing_semantic_vectors_never_trigger_hidden_embedding(semantic_source):
    module, doc, pages, config, tokenizer, _, cache, root = semantic_source
    with pytest.raises(FinsightError, match="semantic_embeddings_missing"):
        module.prepare_semantics(doc, pages, config, tokenizer, cache, root)
    assert not list(root.rglob("*.json"))


def test_unicode_and_empty_page_keep_provenance(page_factory, char_tokenizer, tmp_path):
    module = semantic_module()
    doc, page = page_factory("café € (25) 2022\n" * 35, table_diagnostics=("table_boundary_risk",))
    empty = page.model_copy(update={"page_index": 1, "text": "", "extraction_status": "empty"})
    doc = doc.model_copy(update={"page_count": 2})
    config = SemanticIndexConfig(embedding_dimension=3)
    units = module.semantic_units(doc, (page, empty), config, char_tokenizer)
    assert all(u.page_index == 0 for u in units)
    cache = EmbeddingCache(tmp_path / "emb", config)
    put_vectors(units, cache, [[1, 0, 0]] * len(units))
    prep = module.prepare_semantics(
        doc, (page, empty), config, char_tokenizer, cache, tmp_path / "prep"
    )
    chunks = module.semantic_chunk_pages(doc, (page, empty), config, char_tokenizer, prep)
    assert chunks and all(c.page_start == 0 and c.token_count <= 400 for c in chunks)
    assert chunks[-1].source_spans[0].char_end == len(page.text)
    assert any(d.reason == "max_tokens" for d in prep.decisions)


def test_source_or_configuration_change_invalidates_preparation(semantic_source):
    module, doc, pages, config, tokenizer, units, cache, root = semantic_source
    put_vectors(units, cache, [[1, 0, 0]] * len(units))
    prep = module.prepare_semantics(doc, pages, config, tokenizer, cache, root)
    modified = (pages[0].model_copy(update={"text": pages[0].text + "changed"}),)
    with pytest.raises(FinsightError, match="semantic_preparation_integrity"):
        module.semantic_chunk_pages(doc, modified, config, tokenizer, prep)
    changed = config.model_copy(update={"semantic": SemanticChunkConfig(percentile=90)})
    with pytest.raises(FinsightError, match="semantic_preparation_integrity"):
        module.semantic_chunk_pages(doc, pages, changed, tokenizer, prep)


def test_semantic_index_cannot_silently_use_the_fixed_chunker(index_setup):
    from finsight.indexing.catalog import create_catalog

    _, corpus, repo, _, _, _, _, tokenizer = index_setup
    config = SemanticIndexConfig(
        source_fingerprint=corpus.source_fingerprint, embedding_dimension=3
    )
    with pytest.raises(FinsightError, match="semantic_preparation_missing"):
        create_catalog(corpus, repo, config, tokenizer)


def test_semantic_catalog_index_reopens_from_cache_without_purchasing(index_setup, tmp_path):
    module = semantic_module()
    builder, corpus, repo, _, _, root, context, tokenizer = index_setup
    config = SemanticIndexConfig(
        source_fingerprint=corpus.source_fingerprint, embedding_dimension=3
    )
    cache = EmbeddingCache(tmp_path / "vectors", config)
    all_chunks = []
    for document in corpus.documents:
        pages = tuple(repo.get(document.document_id, i) for i in range(document.page_count))
        units = module.semantic_units(document, pages, config, tokenizer)
        put_vectors(units, cache, [[1, 0, 0]] * len(units))
        prep = module.prepare_semantics(
            document, pages, config, tokenizer, cache, tmp_path / "prep"
        )
        all_chunks.extend(module.semantic_chunk_pages(document, pages, config, tokenizer, prep))
    for chunk in all_chunks:
        cache.put(cache.record(chunk.content, "document", [1, 0, 0]))

    def chunker(document, pages, config, tokenizer):
        prep = module.load_preparation(document, pages, config, tokenizer, cache, tmp_path / "prep")
        return module.semantic_chunk_pages(document, pages, config, tokenizer, prep)

    class CachedOnly:
        def for_run(self, context):
            context.remaining()
            return self

        def embed_documents(self, texts):
            return [list(cache.get(cache.key(t, "document")).vector) for t in texts]

        def embed_query(self, text):
            raise AssertionError("Index lifecycle cannot embed a question")

    manifest = builder.build_index(
        corpus, repo, config, CachedOnly(), root, context, tokenizer=tokenizer, chunker=chunker
    )
    assert manifest.complete and manifest.chunk_count == len(all_chunks)
    reopened = builder.open_index(
        root,
        config,
        corpus,
        pages=repo,
        embeddings=CachedOnly(),
        tokenizer=tokenizer,
        chunker=chunker,
    )
    try:
        assert all(c.chunk_strategy == "semantic" for c in reopened.catalog.chunks)
        assert reopened.manifest == manifest
    finally:
        reopened.store.client.close()


def test_manual_unit_embedding_sends_only_one_bounded_batch(semantic_source, embedding_setup):
    from finsight.runtime.ports import CallContext

    module = importlib.import_module("finsight.chunking.semantic_cache")
    assert hasattr(module, "embed_next_units"), "Missing manual semantic batch"
    embed_next_units = module.embed_next_units

    _, _, _, _, _, units, _, _ = semantic_source
    backend, cache, dispatcher, calls, _ = embedding_setup
    result = embed_next_units(units, cache, backend, CallContext("semantic", 3, 1e20), batch_size=2)
    assert len(calls) == 1 and len(calls[0][1]["input"]) == 2
    assert result["missing_unique_inputs"] == 2
    assert dispatcher.ledger.phase_available(3) < Decimal("0.75")
    assert dispatcher.ledger.snapshot().phase2_available_usd == Decimal("0.75")


def test_manual_semantic_timeout_stops_and_keeps_unknown_reservation(
    semantic_source, embedding_setup
):
    import httpx

    from finsight.runtime.ports import CallContext

    module = importlib.import_module("finsight.chunking.semantic_cache")
    assert hasattr(module, "embed_next_units"), "Missing manual semantic batch"
    embed_next_units = module.embed_next_units

    _, _, _, _, _, units, _, _ = semantic_source
    backend, cache, dispatcher, calls, responses = embedding_setup
    responses.append(httpx.ReadTimeout("synthetic timeout"))
    with pytest.raises(FinsightError, match="provider_timeout"):
        embed_next_units(units, cache, backend, CallContext("semantic-timeout", 3, 1e20))
    assert len(calls) == 1
    assert dispatcher.ledger.snapshot().reserved_usd > 0
    assert all(cache.get(cache.key(u.text, "document")) is None for u in units)
