"""Pure source-aligned semantic units and chunks; never dispatches providers."""

import math
import re
from typing import Literal

from finsight.contracts import Chunk, DocumentManifest, Page, SourceSpan
from finsight.contracts.base import Contract, NonBlank, NonnegativeInt, Sha256, fingerprint
from finsight.contracts.retrieval_experiments import SemanticIndexConfig
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import OffsetTokenizer


class SemanticUnit(Contract):
    unit_id: Sha256
    document_id: NonBlank
    page_index: NonnegativeInt
    source_span: SourceSpan
    text: NonBlank
    token_count: NonnegativeInt


class SemanticDistance(Contract):
    left_unit: Sha256
    right_unit: Sha256
    value: float


class SemanticDecision(Contract):
    source_span: SourceSpan
    reason: Literal["semantic", "max_tokens", "page_end"]


class SemanticPreparation(Contract):
    schema_version: Literal["1"] = "1"
    identity: Sha256
    document_id: NonBlank
    units: tuple[SemanticUnit, ...]
    vector_references: dict[str, dict[str, str]]
    distances: tuple[SemanticDistance, ...]
    threshold: float | None
    decisions: tuple[SemanticDecision, ...]
    payload_fingerprint: Sha256


def _validate_pages(document, pages):
    if len(pages) != document.page_count or any(
        p.document_id != document.document_id or p.page_index != i or p.extraction_status == "error"
        for i, p in enumerate(pages)
    ):
        raise FinsightError("invalid_source_span")


def _bounded_end(text, start, limit, tokenizer):
    offsets = tokenizer.offsets(text[start:])
    if not offsets:
        raise FinsightError("invalid_source_span")
    end = len(text) if len(offsets) <= limit else start + offsets[limit - 1][1]
    while end > start and tokenizer.count(text[start:end]) > limit:
        end -= 1
    if end <= start:
        raise FinsightError("invalid_source_span")
    return end


def semantic_units(
    document: DocumentManifest,
    pages: tuple[Page, ...],
    config: SemanticIndexConfig,
    tokenizer: OffsetTokenizer,
) -> tuple[SemanticUnit, ...]:
    _validate_pages(document, pages)
    units = []
    policy = config.semantic
    for page in pages:
        if not page.text.strip():
            continue
        ends = [m.end() for m in re.finditer(r"\n\s*\n|(?<=[.!?])\s+", page.text)]
        ends.append(len(page.text))
        start = 0
        while start < len(page.text):
            maximum = _bounded_end(page.text, start, policy.unit_max_tokens, tokenizer)
            natural = [
                e
                for e in ends
                if start < e <= maximum
                and tokenizer.count(page.text[start:e]) >= policy.unit_min_tokens
            ]
            end = max(natural) if natural else maximum
            text = page.text[start:end]
            # Whitespace-only fragments belong to their source interval, but need no vector.
            if text.strip():
                span = SourceSpan(page_index=page.page_index, char_start=start, char_end=end)
                identity = fingerprint(
                    dict(
                        document=document.document_id,
                        pdf=document.sha256,
                        parser=page.parser_version,
                        policy=[policy.algorithm, policy.unit_min_tokens, policy.unit_max_tokens],
                        span=span.model_dump(),
                        text=text,
                    )
                )
                units.append(
                    SemanticUnit(
                        unit_id=identity,
                        document_id=document.document_id,
                        page_index=page.page_index,
                        source_span=span,
                        text=text,
                        token_count=tokenizer.count(text),
                    )
                )
            start = end
    return tuple(units)


def preparation_identity(document, pages, config, tokenizer):
    artifact = getattr(tokenizer, "artifact", None)
    return fingerprint(
        dict(
            document=document.model_dump(mode="json"),
            pages=[p.model_dump(mode="json") for p in pages],
            tokenizer=artifact.fingerprint() if artifact else type(tokenizer).__name__,
            semantic=config.semantic.model_dump(mode="json"),
            limits=[config.chunk_tokens, config.overlap_tokens],
            embedding=[
                config.embedding_model,
                config.embedding_revision,
                config.embedding_dimension,
            ],
        )
    )


def threshold_for(distances, percentile):
    positive = sorted(d.value for d in distances if d.value > 0)
    if not positive:
        return None
    position = (len(positive) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return positive[lower] + (positive[upper] - positive[lower]) * (position - lower)


def boundary_decisions(pages, config, tokenizer, units, distances, threshold):
    cuts = {}
    by_id = {u.unit_id: u for u in units}
    if threshold is not None:
        for distance in distances:
            if distance.value > 0 and distance.value >= threshold:
                left, right = by_id[distance.left_unit], by_id[distance.right_unit]
                if left.page_index != right.page_index:
                    raise FinsightError("semantic_preparation_integrity")
                cuts.setdefault(left.page_index, []).append(left.source_span.char_end)
    decisions = []
    for page in pages:
        if not page.text.strip():
            continue
        start, covered_end = 0, 0
        while start < len(page.text):
            maximum = _bounded_end(page.text, start, config.chunk_tokens, tokenizer)
            eligible = [
                e
                for e in cuts.get(page.page_index, ())
                if covered_end < e <= maximum
                and tokenizer.count(page.text[covered_end:e]) >= config.semantic.minimum_new_tokens
            ]
            if eligible:
                end, reason = min(eligible), "semantic"
            else:
                end = maximum
                reason = "page_end" if end == len(page.text) else "max_tokens"
            span = SourceSpan(page_index=page.page_index, char_start=start, char_end=end)
            decisions.append(SemanticDecision(source_span=span, reason=reason))
            if end == len(page.text):
                break
            covered_end = end
            offsets = tokenizer.offsets(page.text[start:end])
            overlap = min(config.overlap_tokens, len(offsets) - 1)
            next_start = end if not overlap else start + offsets[-overlap][0]
            start = max(start + 1, min(end, next_start))
    return tuple(decisions)


def semantic_chunk_pages(
    document: DocumentManifest,
    pages: tuple[Page, ...],
    config: SemanticIndexConfig,
    tokenizer: OffsetTokenizer,
    preparation: SemanticPreparation,
) -> tuple[Chunk, ...]:
    _validate_pages(document, pages)
    if (
        preparation.identity != preparation_identity(document, pages, config, tokenizer)
        or preparation.document_id != document.document_id
        or preparation.units != semantic_units(document, pages, config, tokenizer)
        or preparation.payload_fingerprint
        != fingerprint(preparation.model_dump(mode="json", exclude={"payload_fingerprint"}))
    ) or preparation.decisions != boundary_decisions(
        pages, config, tokenizer, preparation.units, preparation.distances, preparation.threshold
    ):
        raise FinsightError("semantic_preparation_integrity")
    chunks = []
    for decision in preparation.decisions:
        span = decision.source_span
        page = pages[span.page_index]
        text = page.text[span.char_start : span.char_end]
        if not text.strip():
            continue
        chunks.append(
            Chunk(
                chunk_id=fingerprint(
                    dict(
                        document=document.document_id,
                        pdf=document.sha256,
                        parser=page.parser_version,
                        config=config.fingerprint(),
                        span=span.model_dump(),
                        content=text,
                        preparation=preparation.payload_fingerprint,
                    )
                ),
                document_id=document.document_id,
                page_start=span.page_index,
                page_end=span.page_index,
                source_spans=(span,),
                chunk_strategy="semantic",
                config_fingerprint=config.fingerprint(),
                content=text,
                token_count=tokenizer.count(text),
            )
        )
    return tuple(chunks)


# Public convenience exports keep notebook calls explicit without an extra facade.
def prepare_semantics(*args, **kwargs):
    from .semantic_cache import prepare_semantics as prepare

    return prepare(*args, **kwargs)


def load_preparation(*args, **kwargs):
    from .semantic_cache import load_preparation as load

    return load(*args, **kwargs)
