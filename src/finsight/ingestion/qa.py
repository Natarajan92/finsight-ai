"""Source-only mechanical page diagnostics, not semantic table certification."""

from collections.abc import Iterable

from finsight.contracts.documents import Page


def summarize_pages(pages: Iterable[Page]) -> dict[str, int]:
    result = dict.fromkeys(
        (
            "pages",
            "ok",
            "empty",
            "error",
            "layout_mapping_failed",
            "image_content_without_text",
            "readable_encrypted_source",
            "actualtext_position_warning",
        ),
        0,
    )
    for page in pages:
        result["pages"] += 1
        result[page.extraction_status] += 1
        result["layout_mapping_failed"] += int("layout_mapping_failed" in page.table_diagnostics)
        result["image_content_without_text"] += int(
            "image_content_without_text" in page.table_diagnostics
        )
        result["readable_encrypted_source"] += int(
            "readable_encrypted_source" in page.table_diagnostics
        )
        result["actualtext_position_warning"] += int(
            "actualtext_position_warning" in page.table_diagnostics
        )
    return result
