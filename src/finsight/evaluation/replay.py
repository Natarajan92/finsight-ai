"""Validate saved runtime evidence against reopened source-derived authorities."""

from finsight.citations.validation import validate_draft
from finsight.contracts import SourceMetadata
from finsight.contracts.base import fingerprint
from finsight.generation.prompts import build_prompt
from finsight.indexing.catalog import page_key
from finsight.ingestion.manifest import company_key
from finsight.runtime.errors import FinsightError


def _require(condition):
    if not condition:
        raise FinsightError("campaign_integrity")


def validate_campaign_trace(trace, request, catalog, corpus, pages, config, index_id, rate_id):
    _require(
        trace.request == request
        and trace.request_fingerprint == fingerprint(request.model_dump(mode="json"))
        and trace.filters == request.model_dump(mode="json", exclude={"question"})
        and trace.budget_id == config.budget_id
        and trace.index_fingerprint == index_id
        and trace.config_fingerprint == config.fingerprint()
        and trace.source_fingerprint == corpus.source_fingerprint
        and trace.rate_fingerprint == rate_id
    )
    chunks = catalog.chunks_by_id
    documents = {d.document_id: d for d in corpus.documents}
    sources = {
        identity: SourceMetadata(**doc.model_dump(include=set(SourceMetadata.model_fields)))
        for identity, doc in documents.items()
    }
    retrieved = {}
    _require(len(trace.retrieved) <= config.candidate_count)
    for rank, candidate in enumerate(trace.retrieved, 1):
        chunk = chunks.get(candidate.chunk.chunk_id)
        _require(chunk is not None)
        _require(
            candidate.chunk == chunk
            and candidate.rank == rank
            and chunk.chunk_id not in retrieved
            and candidate.source == sources[chunk.document_id]
            and candidate.score.kind == "cosine_distance"
            and candidate.score.direction == "lower_is_better"
        )
        document = documents[chunk.document_id]
        _require(
            (
                request.company is None
                or company_key(request.company) == company_key(document.company or "")
            )
            and (request.period is None or request.period == document.fiscal_period)
            and (request.document_ids is None or chunk.document_id in request.document_ids)
        )
        retrieved[chunk.chunk_id] = candidate
    packet = trace.packet
    if packet is not None:
        _require(packet.token_count <= config.context_tokens)
        seen_ids, covered, verified = set(), {}, set()
        _require(set(packet.dropped_ids) <= set(retrieved))
        _require(len({s.chunk_id for s in packet.slices}) <= request.top_k)
        for evidence in packet.slices:
            candidate = retrieved.get(evidence.chunk_id)
            _require(candidate is not None)
            chunk = candidate.chunk
            _require(
                evidence.document_id == chunk.document_id
                and evidence.page_index == chunk.page_start
                and evidence.source == sources[chunk.document_id]
                and evidence.score == candidate.score
                and len(evidence.source_spans) == 1
                and evidence.evidence_id not in seen_ids
                and evidence.evidence_id
                == fingerprint(
                    {
                        "chunk_id": chunk.chunk_id,
                        "spans": [s.model_dump() for s in evidence.source_spans],
                    }
                )
            )
            if chunk.document_id not in verified and hasattr(pages, "validate"):
                pages.validate(chunk.document_id)
                verified.add(chunk.document_id)
            page = pages.get(chunk.document_id, evidence.page_index)
            span = evidence.source_spans[0]
            _require(
                any(
                    indexed.page_index == span.page_index
                    and indexed.char_start <= span.char_start < span.char_end <= indexed.char_end
                    for indexed in chunk.source_spans
                )
                and fingerprint(page.model_dump(mode="json"))
                == catalog.page_fingerprints[page_key(chunk.document_id, evidence.page_index)]
                and page.text[span.char_start : span.char_end] == evidence.text
            )
            key = (chunk.document_id, span.page_index)
            intervals = covered.setdefault(key, [])
            _require(all(span.char_end <= a or span.char_start >= b for a, b in intervals))
            intervals.append((span.char_start, span.char_end))
            seen_ids.add(evidence.evidence_id)
    if trace.prompt is not None:
        _require(packet is not None and bool(packet.slices))
        expected = build_prompt(request, packet)
        _require(trace.prompt == expected and trace.prompt_fingerprint == expected.fingerprint)
    else:
        _require(trace.prompt_fingerprint is None and trace.draft is None)
    if trace.answer.status in {"answered", "partial"}:
        _require(trace.draft is not None and packet is not None and trace.prompt is not None)
    if trace.draft is not None and trace.answer.status != "error":
        _require(
            validate_draft(trace.draft, packet, pages, trace.answer.usage, request=request)
            == trace.answer
        )
