"""PyMuPDF source inspection; never reads benchmark question JSON."""

from pathlib import Path

import pymupdf

from finsight.contracts.documents import DocumentManifest, Page, SourceSpan, TextBlock
from finsight.contracts.ingestion import ExtractionConfig

from .fingerprints import sha256_file


def inspect_pdf(pdf_path: Path) -> int:
    try:
        with pymupdf.open(pdf_path) as document:
            if not document.is_pdf or document.needs_pass or document.page_count < 1:
                raise ValueError("Expected an unencrypted PDF with at least one page")
            return document.page_count
    except (RuntimeError, OSError, ValueError) as exc:
        raise ValueError(f"Cannot inspect PDF {pdf_path.name}") from exc


def parser_versions() -> dict[str, str]:
    return {"pymupdf": pymupdf.pymupdf_version, "mupdf": pymupdf.mupdf_version}


def _blocks(page: pymupdf.Page, text: str, config: ExtractionConfig) -> tuple[TextBlock, ...]:
    result = []
    cursor = 0
    for block in page.get_text("blocks", sort=config.sort, flags=config.text_flags):
        if block[6] != 0 or not block[4].strip():
            continue
        start = text.find(block[4], cursor)
        if start < 0:
            raise ValueError("Block has no ordered exact source span")
        cursor = start + len(block[4])
        result.append(
            TextBlock(
                block_index=block[5],
                bbox=block[:4],
                text=block[4],
                source_span=SourceSpan(page_index=page.number, char_start=start, char_end=cursor),
            )
        )
    return tuple(result)


def extract_pages(
    pdf_path: Path, document: DocumentManifest, config: ExtractionConfig
) -> tuple[Page, ...]:
    if sha256_file(pdf_path) != document.sha256:
        raise ValueError("Source PDF hash changed")
    if inspect_pdf(pdf_path) != document.page_count:
        raise ValueError("Source page count changed")
    versions = parser_versions()
    parser = f"PyMuPDF/{versions['pymupdf']};MuPDF/{versions['mupdf']};{config.extractor_version}"
    pages = []
    with pymupdf.open(pdf_path) as source:
        for index in range(document.page_count):
            try:
                page = source[index]
                text = page.get_text("text", sort=config.sort, flags=config.text_flags)
            except (RuntimeError, ValueError):
                pages.append(
                    Page(
                        document_id=document.document_id,
                        page_index=index,
                        text="",
                        extraction_status="error",
                        parser_version=parser,
                        table_diagnostics=("pdf_extraction_error",),
                    )
                )
                continue
            diagnostics = [] if text.strip() else ["empty_page"]
            if not text.strip() and page.get_images():
                diagnostics.append("image_content_without_text")
            try:
                blocks = _blocks(page, text, config)
            except (RuntimeError, ValueError):
                blocks = ()
                diagnostics.append("layout_mapping_failed")
            pages.append(
                Page(
                    document_id=document.document_id,
                    page_index=index,
                    text=text,
                    extraction_status="ok" if text.strip() else "empty",
                    parser_version=parser,
                    table_diagnostics=tuple(diagnostics),
                    text_blocks=blocks,
                )
            )
    if sha256_file(pdf_path) != document.sha256:
        raise ValueError("Source PDF hash changed during extraction")
    return tuple(pages)
