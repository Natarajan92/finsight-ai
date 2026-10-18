"""Source-only mechanical page diagnostics, not semantic table certification."""

from collections.abc import Iterable

from finsight.contracts.documents import Page


def summarize_pages(pages: Iterable[Page]) -> dict[str, int]:
    result = dict.fromkeys(("pages", "ok", "empty", "error", "layout_mapping_failed"), 0)
    for page in pages:
        result["pages"] += 1
        result[page.extraction_status] += 1
        result["layout_mapping_failed"] += int("layout_mapping_failed" in page.table_diagnostics)
    return result
