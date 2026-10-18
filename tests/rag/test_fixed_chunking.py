"""Windows preserve exact Unicode occurrences and stay on their original page."""

import importlib

import pytest

from finsight.contracts import BaselineConfig
from finsight.runtime.errors import FinsightError


def chunker():
    assert importlib.util.find_spec("finsight.chunking.fixed"), "Missing fixed chunker"
    return importlib.import_module("finsight.chunking.fixed").chunk_pages


def test_exact_windows_and_stable_ids(page_factory, char_tokenizer):
    document, page = page_factory("x" * 800)
    config = BaselineConfig()
    chunks = chunker()(document, (page,), config, char_tokenizer)
    assert [(c.source_spans[0].char_start, c.source_spans[0].char_end) for c in chunks] == [
        (0, 400),
        (340, 740),
        (680, 800),
    ]
    assert chunks == chunker()(document, (page,), config, char_tokenizer)
    changed = chunker()(document, (page,), BaselineConfig(overlap_tokens=50), char_tokenizer)
    assert chunks[0].chunk_id != changed[0].chunk_id


def test_unicode_and_repeated_rows_keep_correct_occurrence(page_factory, char_tokenizer):
    text = "2022 | USD millions\nRevenue (25) – €1,000\n" * 30
    document, page = page_factory(text)
    chunks = chunker()(document, (page,), BaselineConfig(), char_tokenizer)
    covered = set()
    for chunk in chunks:
        span = chunk.source_spans[0]
        assert chunk.content == text[span.char_start : span.char_end]
        assert chunk.token_count <= 400
        covered.update(range(span.char_start, span.char_end))
    assert covered == set(range(len(text)))


def test_page_boundaries_never_overlap(page_factory, char_tokenizer):
    document, page = page_factory("x" * 401)
    document = document.model_copy(update={"page_count": 2})
    next_page = page.model_copy(update={"page_index": 1})
    chunks = chunker()(document, (page, next_page), BaselineConfig(), char_tokenizer)
    assert {c.page_start for c in chunks} == {0, 1}
    assert all(c.page_start == c.page_end and len(c.source_spans) == 1 for c in chunks)


def test_empty_pages_emit_no_chunks_but_keep_diagnostics(page_factory, char_tokenizer):
    document, page = page_factory("", extraction_status="empty", table_diagnostics=("blank_page",))
    assert chunker()(document, (page,), BaselineConfig(), char_tokenizer) == ()
    assert page.table_diagnostics == ("blank_page",)


def test_wrong_document_or_error_page_rejected(page_factory, char_tokenizer):
    document, page = page_factory()
    for changed in [
        page.model_copy(update={"document_id": "wrong"}),
        page.model_copy(update={"extraction_status": "error"}),
        page.model_copy(update={"page_index": 2}),
    ]:
        with pytest.raises(FinsightError, match="invalid_source_span"):
            chunker()(document, (changed,), BaselineConfig(), char_tokenizer)


def test_table_boundary_risk_is_visible(page_factory, char_tokenizer):
    document, page = page_factory("2022 USD millions\nRevenue 1,000 900\n" * 30)
    chunks = chunker()(document, (page,), BaselineConfig(), char_tokenizer)
    diagnostics = importlib.import_module("finsight.chunking.diagnostics").chunk_diagnostics
    assert any("table_boundary_risk" in diagnostics(c, page) for c in chunks)
