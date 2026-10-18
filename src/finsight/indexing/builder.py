"""Resume compatible builds and publish completion only after full validation."""

import json
from pathlib import Path

from finsight.contracts import BaselineConfig
from finsight.contracts.base import fingerprint
from finsight.contracts.indexing import ChunkCatalog, IndexManifest
from finsight.contracts.ingestion import CorpusManifest
from finsight.ingestion.cache import write_json_atomic
from finsight.retrieval.dense import DenseRetriever
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext, EmbeddingBackend, OffsetTokenizer, PageRepository
from finsight.runtime.software import software_versions

from .catalog import create_catalog, validate_catalog
from .embedding_cache import normalize_vector
from .store import (
    LocalVectorStore,
    chunk_metadata,
    index_build_lock,
)


def open_index(
    root: Path,
    expected: BaselineConfig,
    corpus: CorpusManifest,
    *,
    pages: PageRepository,
    embeddings: EmbeddingBackend,
    tokenizer: OffsetTokenizer,
) -> DenseRetriever:
    if not (root / "manifest.json").is_file():
        raise FinsightError("index_incomplete")
    store = None
    try:
        manifest = IndexManifest.model_validate_json(
            (root / "manifest.json").read_text(encoding="utf-8")
        )
        catalog = ChunkCatalog.model_validate_json(
            (root / "catalog.json").read_text(encoding="utf-8")
        )
        validate_catalog(catalog, corpus, expected, pages, tokenizer)
        if (
            manifest.catalog_fingerprint != catalog.payload_fingerprint
            or manifest.config_fingerprint != expected.fingerprint()
            or manifest.source_fingerprint != corpus.source_fingerprint
            or manifest.chunk_ids != tuple(c.chunk_id for c in catalog.chunks)
            or manifest.chunk_count != len(catalog.chunks)
            or manifest.dimension != expected.embedding_dimension
            or manifest.model != expected.embedding_model
            or manifest.budget_id != expected.budget_id
            or manifest.tokenizer_revision != expected.tokenizer_revision
            or manifest.tokenizer_fingerprint != catalog.tokenizer_fingerprint
            or manifest.software != software_versions()
            or set(manifest.vector_hashes) != set(manifest.chunk_ids)
        ):
            raise FinsightError("index_integrity")
        store = LocalVectorStore(root / "chroma", create=False)
        store.validate(catalog, corpus, manifest.dimension, manifest.vector_hashes, complete=True)
        return DenseRetriever(store, catalog, manifest, corpus, expected, pages, embeddings)
    except FinsightError:
        if store is not None:
            store.client.close()
        raise
    except Exception:
        if store is not None:
            store.client.close()
        raise FinsightError("index_integrity") from None


def build_index(
    corpus: CorpusManifest,
    pages: PageRepository,
    config: BaselineConfig,
    embeddings: EmbeddingBackend,
    root: Path,
    context: CallContext,
    *,
    tokenizer: OffsetTokenizer,
) -> IndexManifest:
    with index_build_lock(root):
        if (root / "manifest.json").exists():
            reopened = open_index(
                root, config, corpus, pages=pages, embeddings=embeddings, tokenizer=tokenizer
            )
            try:
                return reopened.manifest
            finally:
                reopened.store.client.close()
        context.remaining()
        catalog = create_catalog(corpus, pages, config, tokenizer)
        path = root / "catalog.json"
        if path.exists():
            try:
                existing = ChunkCatalog.model_validate_json(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                raise FinsightError("index_integrity") from None
            if existing != catalog:
                raise FinsightError("index_integrity")
        else:
            write_json_atomic(path, catalog.model_dump(mode="json"))
        hashes = {}
        ledger_path = root / "vectors.json"
        if ledger_path.exists():
            try:
                payload = json.loads(ledger_path.read_text(encoding="utf-8"))
                if payload["fingerprint"] != fingerprint(payload["hashes"]):
                    raise ValueError("Vector ledger changed")
                hashes = payload["hashes"]
            except (ValueError, KeyError, OSError):
                raise FinsightError("index_integrity") from None
        with LocalVectorStore(root / "chroma", create=True) as store:
            rows = store.validate(
                catalog, corpus, config.embedding_dimension, hashes, complete=False
            )
            if set(hashes) - set(catalog.chunks_by_id):
                raise FinsightError("index_integrity")
            pending = [
                c for c in catalog.chunks if c.chunk_id not in rows or c.chunk_id not in hashes
            ]
            docs = {d.document_id: d for d in corpus.documents}
            for offset in range(0, len(pending), 16):
                context.remaining()
                batch_context = CallContext(
                    context.run_id,
                    context.phase,
                    min(context.deadline, context.clock() + config.deadline_s),
                    context.clock,
                )
                bound = embeddings.for_run(batch_context)
                batch = pending[offset : offset + 16]
                vectors = bound.embed_documents([c.content for c in batch])
                if len(vectors) != len(batch):
                    raise FinsightError("embedding_shape")
                vectors = [normalize_vector(v, config.embedding_dimension) for v in vectors]
                hashes.update(
                    {
                        c.chunk_id: store.references.put(c.chunk_id, v)
                        for c, v in zip(batch, vectors, strict=True)
                    }
                )
                # Persist vector identity first; a crash can require re-upserting cached vectors.
                write_json_atomic(
                    ledger_path, {"hashes": hashes, "fingerprint": fingerprint(hashes)}
                )
                store.collection.upsert(
                    ids=[c.chunk_id for c in batch],
                    embeddings=vectors,
                    documents=[c.content for c in batch],
                    metadatas=[chunk_metadata(c, docs[c.document_id]) for c in batch],
                )
            store.validate(catalog, corpus, config.embedding_dimension, hashes, complete=True)
            manifest = IndexManifest(
                budget_id=config.budget_id,
                catalog_fingerprint=catalog.payload_fingerprint,
                source_fingerprint=corpus.source_fingerprint,
                config_fingerprint=config.fingerprint(),
                chunk_ids=tuple(c.chunk_id for c in catalog.chunks),
                chunk_count=len(catalog.chunks),
                dimension=config.embedding_dimension,
                model=config.embedding_model,
                tokenizer_revision=config.tokenizer_revision,
                tokenizer_fingerprint=catalog.tokenizer_fingerprint,
                software=software_versions(),
                vector_hashes=hashes,
            )
            write_json_atomic(root / "manifest.json", manifest.model_dump(mode="json"))
            return manifest
