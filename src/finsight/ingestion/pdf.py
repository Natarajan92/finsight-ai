"""PyMuPDF source inspection; never reads benchmark question JSON."""

from pathlib import Path

import pymupdf


def inspect_pdf(pdf_path: Path) -> int:
    try:
        with pymupdf.open(pdf_path) as document:
            if not document.is_pdf or document.needs_pass or document.page_count < 1:
                raise ValueError("Expected an unencrypted PDF with at least one page")
            return document.page_count
    except (RuntimeError, OSError, ValueError) as exc:
        raise ValueError(f"Cannot inspect PDF {pdf_path.name}") from exc
