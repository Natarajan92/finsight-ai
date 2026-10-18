"""Conservative table/heading cut risks; no financial text is reconstructed."""

import re

from finsight.contracts import Chunk, Page


def chunk_diagnostics(chunk: Chunk, page: Page) -> tuple[str, ...]:
    warnings = list(page.table_diagnostics)
    financial = bool(
        re.search(
            r"\b(?:19|20)\d{2}\b|\b(?:million|billion|thousand)s?\b", page.text, re.IGNORECASE
        )
    )
    for span in chunk.source_spans:
        inside_line = (span.char_start > 0 and page.text[span.char_start - 1] != "\n") or (
            span.char_end < len(page.text) and page.text[span.char_end - 1] != "\n"
        )
        inside_block = any(
            b.source_span.char_start < boundary < b.source_span.char_end
            for b in page.text_blocks
            for boundary in (span.char_start, span.char_end)
        )
        if financial and (inside_line or inside_block):
            warnings.append("table_boundary_risk")
        if financial and span.char_start > 0:
            warnings.append("heading_may_be_outside_chunk")
    return tuple(dict.fromkeys(warnings))
