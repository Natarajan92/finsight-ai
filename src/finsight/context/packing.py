"""Subtract only covered intervals; count the complete labeled evidence payload."""

import json

from finsight.chunking.diagnostics import chunk_diagnostics
from finsight.contracts import BaselineConfig, QueryRequest, RetrievalCandidate, SourceSpan
from finsight.contracts.base import fingerprint
from finsight.contracts.context import EvidencePacket, EvidenceSlice
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext, PageRepository, TokenCounter


def render_evidence(slices: tuple[EvidenceSlice, ...]) -> str:
    return json.dumps(
        {
            "evidence": [
                dict(
                    evidence_id=s.evidence_id,
                    chunk_id=s.chunk_id,
                    document_id=s.document_id,
                    filing=s.source.doc_name,
                    company=s.source.company,
                    period=s.source.fiscal_period,
                    pdf_page_index=s.page_index,
                    source_spans=[span.model_dump() for span in s.source_spans],
                    text=s.text,
                )
                for s in slices
            ]
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _subtract(start: int, end: int, covered: list[tuple[int, int]]) -> list[tuple[int, int]]:
    fragments = [(start, end)]
    for left, right in sorted(covered):
        updated = []
        for a, b in fragments:
            if right <= a or left >= b:
                updated.append((a, b))
            else:
                if a < left:
                    updated.append((a, left))
                if right < b:
                    updated.append((right, b))
        fragments = updated
    return fragments


def pack_evidence(
    candidates: tuple[RetrievalCandidate, ...],
    pages: PageRepository,
    request: QueryRequest,
    counter: TokenCounter,
    context: CallContext,
    config: BaselineConfig,
) -> EvidencePacket:
    context.remaining()
    if candidates and not callable(getattr(counter, "count_text", None)):
        raise FinsightError("token_count_unavailable")
    slices = []
    covered = {}
    selected = set()
    dropped = []
    limitations = []
    count = 0
    for candidate in candidates:
        context.remaining()
        chunk = candidate.chunk
        if chunk.chunk_id in selected:
            continue
        if len(selected) >= request.top_k:
            dropped.append(chunk.chunk_id)
            continue
        page = pages.get(chunk.document_id, chunk.page_start)
        if len(chunk.source_spans) != 1:
            raise FinsightError("invalid_source_span")
        span = chunk.source_spans[0]
        if (
            page.document_id != chunk.document_id
            or page.page_index != span.page_index
            or span.char_end > len(page.text)
            or page.extraction_status == "error"
            or page.text[span.char_start : span.char_end] != chunk.content
        ):
            raise FinsightError("invalid_source_span")
        key = (chunk.document_id, span.page_index)
        novel = _subtract(span.char_start, span.char_end, covered.get(key, []))
        additions = []
        for start, end in novel:
            text = page.text[start:end]
            if not text.strip():
                # Whitespace removed by overlap subtraction has no standalone evidence claim.
                continue
            retained = SourceSpan(page_index=span.page_index, char_start=start, char_end=end)
            identity = fingerprint({"chunk_id": chunk.chunk_id, "spans": [retained.model_dump()]})
            additions.append(
                EvidenceSlice(
                    evidence_id=identity,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    page_index=span.page_index,
                    source_spans=(retained,),
                    text=text,
                    source=candidate.source,
                    score=candidate.score,
                    diagnostics=chunk_diagnostics(chunk, page),
                )
            )
        if not additions:
            dropped.append(chunk.chunk_id)
            continue
        estimate = counter.count_text(render_evidence(tuple(slices + additions)), context)
        if type(estimate) is not int or estimate < 0:
            raise FinsightError("token_count_unavailable")
        if estimate > config.context_tokens:
            dropped.append(chunk.chunk_id)
            limitations.append("context_budget_dropped")
            continue
        count = estimate
        slices.extend(additions)
        selected.add(chunk.chunk_id)
        covered.setdefault(key, []).extend(novel)
        limitations.extend(warning for addition in additions for warning in addition.diagnostics)
    return EvidencePacket(
        slices=tuple(slices),
        token_count=count,
        dropped_ids=tuple(dict.fromkeys(dropped)),
        limitations=tuple(dict.fromkeys(limitations)),
    )
