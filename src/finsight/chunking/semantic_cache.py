"""Semantic preparation reconstructed from validated document-role embedding records."""

import math
from pathlib import Path

from finsight.contracts.base import fingerprint
from finsight.indexing.embedding_cache import EmbeddingCache
from finsight.ingestion.cache import write_json_atomic
from finsight.runtime.errors import FinsightError

from .semantic import (
    SemanticDistance,
    SemanticPreparation,
    boundary_decisions,
    preparation_identity,
    semantic_units,
    threshold_for,
)


def _derive(document, pages, config, tokenizer, cache):
    units = semantic_units(document, pages, config, tokenizer)
    refs, distances = {}, []
    previous, previous_vector = None, None
    for unit in units:
        record = cache.get(cache.key(unit.text, "document"))
        if record is None:
            raise FinsightError("semantic_embeddings_missing")
        refs[unit.unit_id] = dict(
            key=record.key,
            payload_fingerprint=record.payload_hash,
            embedding_identity=cache.config_fingerprint,
        )
        if previous is not None and previous.page_index == unit.page_index:
            similarity = math.fsum(
                a * b for a, b in zip(previous_vector, record.vector, strict=True)
            )
            distance = max(0.0, min(2.0, 1.0 - similarity))
            distances.append(
                SemanticDistance(
                    left_unit=previous.unit_id, right_unit=unit.unit_id, value=distance
                )
            )
        previous, previous_vector = unit, record.vector
    threshold = threshold_for(distances, config.semantic.percentile)
    decisions = boundary_decisions(pages, config, tokenizer, units, distances, threshold)
    payload = dict(
        identity=preparation_identity(document, pages, config, tokenizer),
        document_id=document.document_id,
        units=units,
        vector_references=refs,
        distances=distances,
        threshold=threshold,
        decisions=decisions,
    )
    prep = SemanticPreparation(**payload, payload_fingerprint="0" * 64)
    return prep.model_copy(
        update={
            "payload_fingerprint": fingerprint(
                prep.model_dump(mode="json", exclude={"payload_fingerprint"})
            )
        }
    )


def preparation_path(root, document, pages, config, tokenizer):
    return Path(root) / (preparation_identity(document, pages, config, tokenizer) + ".json")


def load_preparation(document, pages, config, tokenizer, cache, root):
    path = preparation_path(root, document, pages, config, tokenizer)
    try:
        stored = SemanticPreparation.model_validate_json(path.read_text(encoding="utf-8"))
        if stored != _derive(document, pages, config, tokenizer, cache):
            raise FinsightError("semantic_preparation_integrity")
        return stored
    except FileNotFoundError:
        raise FinsightError("semantic_preparation_missing") from None
    except (ValueError, OSError):
        raise FinsightError("semantic_preparation_integrity") from None


def prepare_semantics(document, pages, config, tokenizer, cache: EmbeddingCache, root):
    path = preparation_path(root, document, pages, config, tokenizer)
    if path.exists():
        return load_preparation(document, pages, config, tokenizer, cache, root)
    prepared = _derive(document, pages, config, tokenizer, cache)
    write_json_atomic(path, prepared.model_dump(mode="json"))
    return prepared


def cache_progress(units, cache):
    missing = {}
    for unit in units:
        key = cache.key(unit.text, "document")
        if cache.get(key) is None:
            missing.setdefault(key, unit.text)
    return dict(
        total_units=len(units),
        missing_unique_inputs=len(missing),
        missing_texts=tuple(missing.values()),
    )


def embed_next_units(units, cache, backend, context, *, batch_size=4):
    if type(batch_size) is not int or not 1 <= batch_size <= 4:
        raise ValueError("Semantic batch size must be 1..4")
    context.remaining()
    texts = cache_progress(units, cache)["missing_texts"]
    if texts:
        backend.for_run(context).embed_documents(list(texts[:batch_size]))
    return cache_progress(units, cache)
