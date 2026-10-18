"""Page-local windows with hard re-encoded token limits and exact source spans."""

from finsight.contracts import BaselineConfig, Chunk, DocumentManifest, Page, SourceSpan
from finsight.contracts.base import fingerprint
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import OffsetTokenizer


def chunk_pages(
    document: DocumentManifest,
    pages: tuple[Page, ...],
    config: BaselineConfig,
    tokenizer: OffsetTokenizer,
) -> tuple[Chunk, ...]:
    if len(pages) != document.page_count or any(
        p.document_id != document.document_id
        or p.page_index != index
        or p.extraction_status == "error"
        for index, p in enumerate(pages)
    ):
        raise FinsightError("invalid_source_span")
    chunks = []
    config_id = config.fingerprint()
    for page in pages:
        if not page.text.strip():
            continue
        start = 0
        while start < len(page.text):
            remaining = page.text[start:]
            offsets = tokenizer.offsets(remaining)
            if not offsets or any(not 0 <= a < b <= len(remaining) for a, b in offsets):
                raise FinsightError("invalid_source_span")
            end = (
                len(page.text)
                if len(offsets) <= config.chunk_tokens
                else start + offsets[config.chunk_tokens - 1][1]
            )
            # BPE may split a Unicode character across multiple tokens or re-segment at a cut.
            while end > start and tokenizer.count(page.text[start:end]) > config.chunk_tokens:
                end -= 1
            if end <= start or not page.text[start:end].strip():
                raise FinsightError("invalid_source_span", "No source-preserving bounded window")
            text = page.text[start:end]
            span = SourceSpan(page_index=page.page_index, char_start=start, char_end=end)
            identity = fingerprint(
                {
                    "document_id": document.document_id,
                    "pdf": document.sha256,
                    "parser": page.parser_version,
                    "config": config_id,
                    "span": span.model_dump(),
                    "content": text,
                }
            )
            chunks.append(
                Chunk(
                    chunk_id=identity,
                    document_id=document.document_id,
                    page_start=page.page_index,
                    page_end=page.page_index,
                    source_spans=(span,),
                    chunk_strategy="fixed",
                    config_fingerprint=config_id,
                    content=text,
                    token_count=tokenizer.count(text),
                )
            )
            if end == len(page.text):
                break
            local = tokenizer.offsets(text)
            overlap = min(config.overlap_tokens, len(local) - 1)
            next_start = end if overlap == 0 else start + local[-overlap][0]
            start = max(start + 1, min(end, next_start))
    return tuple(chunks)
