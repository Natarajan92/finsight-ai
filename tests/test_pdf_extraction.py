import pymupdf
import pytest
from pydantic import ValidationError

from finsight.contracts import Page, SourceSpan
from finsight.contracts.documents import TextBlock
from finsight.contracts.ingestion import ExtractionConfig
from finsight.ingestion.manifest import build_manifest
from finsight.ingestion.pdf import extract_pages


def test_financial_text_page_zero_and_offsets(pdf_factory, metadata_factory):
    path = pdf_factory()
    doc = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").documents[0]
    pages = extract_pages(path, doc, ExtractionConfig())
    assert len(pages) == 2 and [p.page_index for p in pages] == [0, 1]
    first, blank = pages
    with pymupdf.open(path) as pdf:
        assert first.text == pdf[0].get_text("text", sort=False, flags=pymupdf.TEXTFLAGS_TEXT)
    for value in ("2022", "2021", "USD millions", "1,000", "(25)", "-10", "café"):
        assert value in first.text
    assert first.extraction_status == "ok" and first.text_blocks
    assert blank.extraction_status == "empty" and blank.text == ""
    for block in first.text_blocks:
        assert block.source_span.page_index == 0
        assert first.text[block.source_span.char_start : block.source_span.char_end] == block.text
    assert Page.model_validate_json(first.model_dump_json()) == first
    assert "1.28.2" in first.parser_version


@pytest.mark.parametrize("change", ["hash", "page_count"])
def test_extraction_refuses_changed_source(change, pdf_factory, metadata_factory):
    path = pdf_factory()
    doc = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").documents[0]
    doc = doc.model_copy(update={"sha256": "0" * 64} if change == "hash" else {"page_count": 3})
    with pytest.raises(ValueError):
        extract_pages(path, doc, ExtractionConfig())


@pytest.mark.parametrize("change", ["text", "offset", "page", "bbox", "overlap"])
def test_page_rejects_unproven_blocks(change):
    block = {
        "block_index": 0,
        "bbox": (0, 0, 10, 10),
        "text": "Revenue",
        "source_span": {"page_index": 0, "char_start": 0, "char_end": 7},
    }
    if change == "text":
        block["text"] = "wrong"
    elif change == "offset":
        block["source_span"]["char_end"] = 99
    elif change == "page":
        block["source_span"]["page_index"] = 1
    elif change == "bbox":
        block["bbox"] = (10, 0, 0, 10)
    blocks = [block, block] if change == "overlap" else [block]
    with pytest.raises(ValidationError):
        Page(
            document_id="doc",
            page_index=0,
            text="Revenue",
            extraction_status="ok",
            parser_version="test",
            text_blocks=blocks,
        )


def test_bbox_must_be_finite():
    with pytest.raises(ValidationError):
        TextBlock(
            block_index=0,
            bbox=(0, 0, float("inf"), 10),
            text="a",
            source_span=SourceSpan(page_index=0, char_start=0, char_end=1),
        )


def test_layout_failure_retains_raw_text(pdf_factory, metadata_factory, monkeypatch):
    path = pdf_factory()
    doc = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").documents[0]
    original = pymupdf.Page.get_text

    def broken_blocks(self, option="text", **kwargs):
        if option == "blocks":
            return [(0, 0, 10, 10, "does not match raw page", 0, 0)]
        return original(self, option, **kwargs)

    monkeypatch.setattr(pymupdf.Page, "get_text", broken_blocks)
    first = extract_pages(path, doc, ExtractionConfig())[0]
    assert "Revenue" in first.text and first.extraction_status == "ok"
    assert first.text_blocks == () and "layout_mapping_failed" in first.table_diagnostics


def test_extraction_error_keeps_page_identity(pdf_factory, metadata_factory, monkeypatch):
    path = pdf_factory()
    doc = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1").documents[0]

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic parser error")

    monkeypatch.setattr(pymupdf.Page, "get_text", fail)
    pages = extract_pages(path, doc, ExtractionConfig())
    assert [p.page_index for p in pages] == [0, 1]
    assert all(p.extraction_status == "error" for p in pages)


def test_multi_column_preserves_original_order(pdf_factory, metadata_factory):
    path = pdf_factory(texts=[""])
    with pymupdf.open(path) as doc:
        doc[0].insert_text((300, 70), "2021\n900\n(10)")
        doc[0].insert_text((50, 70), "2022\n1,000\n(25)")
        doc.saveIncr()
    manifest = build_manifest(metadata_factory(), path.parent, ("AMD",), "v1")
    page = extract_pages(path, manifest.documents[0], ExtractionConfig())[0]
    assert page.text.index("2021") < page.text.index("2022")
    assert len(page.text_blocks) == 2
