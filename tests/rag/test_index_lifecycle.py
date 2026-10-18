"""Incomplete, stale or altered indexes must fail before any generation."""

import json

import pytest

from finsight.runtime.errors import FinsightError


def build(setup):
    module, corpus, repo, config, embeddings, root, context, tokenizer = setup
    return module.build_index(corpus, repo, config, embeddings, root, context, tokenizer=tokenizer)


def reopen(setup, **changes):
    module, corpus, repo, config, embeddings, root, _, tokenizer = setup
    return module.open_index(
        root,
        changes.get("config", config),
        corpus,
        pages=repo,
        embeddings=embeddings,
        tokenizer=tokenizer,
    )


def test_second_complete_build_makes_zero_embedding_calls(index_setup):
    manifest = build(index_setup)
    embeddings = index_setup[4]
    before = embeddings.calls
    assert build(index_setup) == manifest
    assert embeddings.calls == before
    retriever = reopen(index_setup)
    assert set(retriever.catalog.chunks_by_id) == set(manifest.chunk_ids)
    assert manifest.complete is True


def test_incomplete_index_never_opens_and_build_resumes(index_setup):
    build(index_setup)
    root = index_setup[5]
    (root / "manifest.json").unlink()
    with pytest.raises(FinsightError, match="index_incomplete"):
        reopen(index_setup)
    assert build(index_setup).complete


@pytest.mark.parametrize("target", ["catalog.json", "manifest.json"])
def test_catalog_or_manifest_tamper_rejected(index_setup, target):
    build(index_setup)
    path = index_setup[5] / target
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_fingerprint"] = "a" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FinsightError, match="index_integrity"):
        reopen(index_setup)


def test_wrong_config_dimension_refuses_reuse(index_setup):
    build(index_setup)
    changed = index_setup[3].model_copy(update={"embedding_dimension": 4})
    with pytest.raises(FinsightError, match="index_integrity"):
        reopen(index_setup, config=changed)


@pytest.mark.parametrize("field,value", [("document_id", "forged"), ("company", "other")])
def test_stored_filter_metadata_tamper_rejected(index_setup, field, value):
    build(index_setup)
    retriever = reopen(index_setup)
    raw = retriever.store.collection.get()
    changed = dict(raw["metadatas"][0])
    changed[field] = value
    retriever.store.collection.update(ids=[raw["ids"][0]], metadatas=[changed])
    with pytest.raises(FinsightError, match="index_integrity"):
        reopen(index_setup)


def test_stored_text_or_vector_tamper_rejected(index_setup):
    build(index_setup)
    retriever = reopen(index_setup)
    identity = retriever.manifest.chunk_ids[0]
    retriever.store.collection.update(
        ids=[identity], documents=["altered source"], embeddings=[[0.0, 1.0, 0.0]]
    )
    with pytest.raises(FinsightError, match="index_integrity"):
        reopen(index_setup)


def test_replaced_original_or_altered_page_cache_fails(index_setup):
    build(index_setup)
    repo = index_setup[2]
    doc = index_setup[1].documents[0]
    path = repo.pdf_root / doc.local_path
    original = path.read_bytes()
    path.write_bytes(original + b"changed")
    with pytest.raises(FinsightError, match="source_integrity"):
        reopen(index_setup)
    path.write_bytes(original)
    from finsight.ingestion.cache import cache_path

    cache_path(doc, repo.extraction, repo.cache_root).write_text("{}")
    with pytest.raises(FinsightError, match="source_integrity"):
        reopen(index_setup)


def test_self_consistent_removed_chunk_rejected_against_source_windows(index_setup):
    from finsight.contracts.base import fingerprint
    from finsight.ingestion.cache import write_json_atomic

    build(index_setup)
    retriever = reopen(index_setup)
    removed = retriever.catalog.chunks[0].chunk_id
    catalog = retriever.catalog.model_copy(update={"chunks": retriever.catalog.chunks[1:]})
    catalog = catalog.model_copy(
        update={
            "payload_fingerprint": fingerprint(
                catalog.model_dump(mode="json", exclude={"payload_fingerprint"})
            )
        }
    )
    manifest = retriever.manifest.model_copy(
        update={
            "catalog_fingerprint": catalog.payload_fingerprint,
            "chunk_ids": tuple(c.chunk_id for c in catalog.chunks),
            "chunk_count": len(catalog.chunks),
            "vector_hashes": {
                k: v for k, v in retriever.manifest.vector_hashes.items() if k != removed
            },
        }
    )
    retriever.store.collection.delete(ids=[removed])
    root = index_setup[5]
    write_json_atomic(root / "catalog.json", catalog.model_dump(mode="json"))
    write_json_atomic(root / "manifest.json", manifest.model_dump(mode="json"))
    with pytest.raises(FinsightError, match="index_integrity"):
        reopen(index_setup)


def test_vector_integrity_validation_is_paginated(index_setup, monkeypatch):
    build(index_setup)
    retriever = reopen(index_setup)
    collection_type = type(retriever.store.collection)
    original = collection_type.get

    def bounded_get(self, *args, **kwargs):
        if "embeddings" in kwargs.get("include", []):
            assert 0 < kwargs.get("limit", 0) <= 128, "Unbounded vector materialization"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(collection_type, "get", bounded_get)
    reopen(index_setup)


def test_interrupted_build_resumes_only_remaining_batches(index_setup):
    import math

    from finsight.indexing.store import LocalVectorStore

    setup = list(index_setup)
    setup[3] = setup[3].model_copy(update={"chunk_tokens": 40, "overlap_tokens": 5})
    embeddings = setup[4]
    embeddings.fail_after = 1
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        build(setup)
    stored = LocalVectorStore(setup[5] / "chroma", create=False).collection.count()
    assert stored == 16
    with pytest.raises(FinsightError, match="index_incomplete"):
        reopen(setup)
    embeddings.fail_after = None
    before = embeddings.calls
    result = build(setup)
    assert embeddings.calls == before + math.ceil((result.chunk_count - stored) / 16)


def test_each_index_batch_has_a_bounded_attempt_context(index_setup, monkeypatch):
    embeddings = index_setup[4]
    contexts = []

    def capture(context):
        contexts.append(context)
        return embeddings

    monkeypatch.setattr(embeddings, "for_run", capture)
    build(index_setup)
    assert contexts and all(c.deadline - c.clock() <= 45 for c in contexts)


def test_failed_reopen_releases_its_client(index_setup, monkeypatch):
    from finsight.indexing.store import LocalVectorStore

    build(index_setup)
    created = []
    original = LocalVectorStore.__init__

    def capture(self, *args, **kwargs):
        original(self, *args, **kwargs)
        created.append(self)

    def reject(*args, **kwargs):
        raise FinsightError("index_integrity")

    monkeypatch.setattr(LocalVectorStore, "__init__", capture)
    monkeypatch.setattr(LocalVectorStore, "validate", reject)
    with pytest.raises(FinsightError, match="index_integrity"):
        reopen(index_setup)
    assert created[0].client._closed
