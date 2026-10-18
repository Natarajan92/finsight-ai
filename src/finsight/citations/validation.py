"""Validate citation integrity; semantic claim support remains a separate judgment."""

from finsight.contracts import Answer, Evidence, QueryRequest, UsageMetrics
from finsight.contracts.context import EvidencePacket, EvidenceSlice
from finsight.contracts.generation import DraftAnswer
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import PageRepository

GAP = "\n[gap]\n"


def source_fragments(item: EvidenceSlice, pages: PageRepository) -> tuple[str, ...]:
    if hasattr(pages, "validate"):
        pages.validate(item.document_id)
    page = pages.get(item.document_id, item.page_index)
    if (
        page.document_id != item.document_id
        or page.page_index != item.page_index
        or page.extraction_status == "error"
        or not item.source_spans
    ):
        raise FinsightError("citation_validation_failed")
    parts = []
    previous = 0
    for span in item.source_spans:
        if (
            span.page_index != item.page_index
            or span.char_start < previous
            or span.char_end > len(page.text)
        ):
            raise FinsightError("citation_validation_failed")
        parts.append(page.text[span.char_start : span.char_end])
        previous = span.char_end
    if GAP.join(parts) != item.text:
        raise FinsightError("citation_validation_failed")
    return tuple(parts)


def packet_map(packet: EvidencePacket) -> dict[str, EvidenceSlice]:
    result = {s.evidence_id: s for s in packet.slices}
    if len(result) != len(packet.slices):
        raise FinsightError("citation_validation_failed")
    return result


def resolve_reference(
    identity: str, quote: str, items: dict[str, EvidenceSlice], pages: PageRepository
) -> Evidence:
    item = items.get(identity)
    if (
        item is None
        or not quote.strip()
        or not any(quote in part for part in source_fragments(item, pages))
    ):
        raise FinsightError("citation_validation_failed")
    return Evidence(
        chunk_id=item.chunk_id,
        document_id=item.document_id,
        page_index=item.page_index,
        source_quote=quote,
        score=item.score,
        source=item.source,
    )


def validate_draft(
    draft: DraftAnswer,
    packet: EvidencePacket,
    pages: PageRepository,
    usage: UsageMetrics,
    *,
    request: QueryRequest | None = None,
) -> Answer:
    try:
        draft = DraftAnswer.model_validate(draft.model_dump(mode="json"))
    except (ValueError, TypeError):
        raise FinsightError("citation_validation_failed") from None
    limitations = tuple(dict.fromkeys((*draft.limitations, *packet.limitations)))
    if draft.status == "insufficient_evidence":
        return Answer(status="insufficient_evidence", limitations=limitations, usage=usage)
    items = packet_map(packet)
    citations = []
    labels = {}
    lines = []
    for claim in draft.claims:
        numbers = []
        for reference in claim.references:
            evidence = resolve_reference(reference.evidence_id, reference.quote, items, pages)
            key = (reference.evidence_id, reference.quote)
            if key not in labels:
                citations.append(evidence)
                labels[key] = len(citations)
            numbers.append(labels[key])
        lines.append(claim.text + " " + " ".join(f"[{n}]" for n in dict.fromkeys(numbers)))
    calculation = None
    if draft.calculation is not None:
        from .calculation import validate_calculation

        calculation = validate_calculation(draft.calculation, packet, pages, request=request)
        for operand in draft.calculation.operands:
            key = (operand.evidence_id, operand.source_text)
            if key not in labels:
                citations.append(resolve_reference(*key, items, pages))
                labels[key] = len(citations)
    return Answer(
        status=draft.status,
        answer_text="\n".join(lines),
        citations=tuple(citations),
        limitations=limitations,
        calculation=calculation,
        usage=usage,
    )
