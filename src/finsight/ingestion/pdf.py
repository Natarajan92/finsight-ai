"""PyMuPDF source inspection; never reads benchmark question JSON."""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from finsight.contracts.documents import DocumentManifest, Page, SourceSpan, TextBlock
from finsight.contracts.ingestion import ExtractionConfig

from .fingerprints import sha256_file
from .source_policy import READABLE_ENCRYPTED_SHA256

_ACTUALTEXT_WARNING = "ActualText with no position. Text may be lost or mispositioned."


def _page_warning_diagnostics() -> tuple[str, ...]:
    lines = pymupdf.TOOLS.mupdf_warnings().splitlines()
    if not lines:
        return ()
    # Preserve known text-quality uncertainty; never suppress syntax/unknown errors.
    if all(
        line == _ACTUALTEXT_WARNING
        or (
            index > 0
            and lines[index - 1] == _ACTUALTEXT_WARNING
            and re.fullmatch(r"\.\.\. repeated \d+ times\.\.\.", line)
        )
        for index, line in enumerate(lines)
    ):
        return ("actualtext_position_warning",)
    raise ValueError("pdf_parser_warning")


@dataclass(frozen=True)
class PdfInspection:
    page_count: int
    encryption_method: str | None


def inspect_pdf(pdf_path: Path) -> int:
    return inspect_pdf_details(pdf_path).page_count


def inspect_pdf_details(pdf_path: Path) -> PdfInspection:
    # MuPDF's warning buffer is process-global. This offline adapter is serial.
    pymupdf.TOOLS.reset_mupdf_warnings()
    try:
        with pymupdf.open(pdf_path) as document:
            if (
                not document.is_pdf
                or document.needs_pass
                or document.is_repaired
                or document.page_count < 1
                or pymupdf.TOOLS.mupdf_warnings()
            ):
                raise ValueError("Expected a structurally intact readable PDF")
            encryption = document.metadata.get("encryption")
            if encryption and (
                sha256_file(pdf_path) not in READABLE_ENCRYPTED_SHA256
                or not document.permissions & pymupdf.PDF_PERM_COPY
            ):
                raise ValueError("Encrypted source lacks exact approval or copy permission")
            return PdfInspection(document.page_count, encryption)
    except (RuntimeError, OSError, ValueError) as exc:
        raise ValueError(f"Cannot inspect PDF {pdf_path.name}") from exc
    finally:
        pymupdf.TOOLS.reset_mupdf_warnings()


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
    inspection = inspect_pdf_details(pdf_path)
    if inspection.page_count != document.page_count:
        raise ValueError("Source page count changed")
    versions = parser_versions()
    parser = f"PyMuPDF/{versions['pymupdf']};MuPDF/{versions['mupdf']};{config.extractor_version}"
    pages = []
    with pymupdf.open(pdf_path) as source:
        for index in range(document.page_count):
            pymupdf.TOOLS.reset_mupdf_warnings()
            try:
                page = source[index]
                text = page.get_text("text", sort=config.sort, flags=config.text_flags)
                diagnostics = [] if text.strip() else ["empty_page"]
                if inspection.encryption_method:
                    diagnostics.append("readable_encrypted_source")
                if not text.strip() and page.get_images():
                    diagnostics.append("image_content_without_text")
                try:
                    blocks = _blocks(page, text, config)
                except (RuntimeError, ValueError):
                    blocks = ()
                    diagnostics.append("layout_mapping_failed")
                diagnostics.extend(_page_warning_diagnostics())
            except (RuntimeError, ValueError) as exc:
                warning = bool(pymupdf.TOOLS.mupdf_warnings()) or str(exc) == "pdf_parser_warning"
                pymupdf.TOOLS.reset_mupdf_warnings()
                pages.append(
                    Page(
                        document_id=document.document_id,
                        page_index=index,
                        text="",
                        extraction_status="error",
                        parser_version=parser,
                        table_diagnostics=(
                            "pdf_parser_warning" if warning else "pdf_extraction_error",
                        ),
                    )
                )
                continue
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
