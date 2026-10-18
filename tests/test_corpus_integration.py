"""Opt-in checks over unchanged, locally supplied FinanceBench source files."""

import hashlib
import os
from collections import Counter
from pathlib import Path

import pytest

from finsight.contracts.ingestion import CorpusManifest, ExtractionConfig
from finsight.evaluation.benchmark import load_benchmark
from finsight.evaluation.splits import (
    SplitManifest,
    SplitPolicy,
    freeze_splits,
    validate_split_pair,
)
from finsight.ingestion import cache
from finsight.ingestion.fingerprints import sha256_file
from finsight.ingestion.manifest import COMPANIES, build_manifest
from finsight.ingestion.qa import summarize_pages

pytestmark = pytest.mark.integration
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def real_inputs():
    pdfs = os.environ.get("FINSIGHT_SOURCE_PDF_DIR")
    benchmark = os.environ.get("FINSIGHT_BENCHMARK_DIR")
    if not pdfs or not benchmark:
        pytest.skip("Set FINSIGHT_SOURCE_PDF_DIR and FINSIGHT_BENCHMARK_DIR for local-data checks")
    pdf_root, benchmark_root = Path(pdfs), Path(benchmark)
    if not pdf_root.is_dir() or not benchmark_root.is_dir():
        pytest.fail("Explicit local FinanceBench paths do not exist")
    corpus = CorpusManifest.model_validate_json(
        (REPO / "data/manifests/financebench-selected.json").read_text(encoding="utf-8")
    )
    return pdf_root, benchmark_root, corpus


def test_all_canonical_filings_match_immutable_manifest(real_inputs):
    pdf_root, benchmark_root, corpus = real_inputs
    rebuilt = build_manifest(
        benchmark_root / "financebench_document_information.jsonl", pdf_root, COMPANIES, "phase1-v1"
    )
    assert rebuilt == corpus
    assert len(corpus.documents) == 53 and sum(d.page_count for d in corpus.documents) == 9504
    assert Counter(d.company for d in corpus.documents) == Counter(
        d.company for d in rebuilt.documents
    )
    assert sum(d.code == "duplicate_alias" for d in corpus.diagnostics) == 2
    assert sum(d.code == "readable_encrypted_source" for d in corpus.diagnostics) == 9


def test_every_cached_page_is_complete_without_reparsing(real_inputs, monkeypatch):
    pdf_root, _, corpus = real_inputs

    def never_parse(*args, **kwargs):
        raise AssertionError("A complete valid cache must not reparse source PDFs")

    monkeypatch.setattr(cache, "extract_pages", never_parse)
    totals = Counter()
    for document in corpus.documents:
        pages = cache.extract_cached(
            pdf_root, document, ExtractionConfig(), REPO / "data/cache/pages"
        )
        assert [p.page_index for p in pages] == list(range(document.page_count))
        assert all(page.text_blocks for page in pages if page.extraction_status == "ok")
        totals.update(summarize_pages(pages))
    assert totals == {
        "pages": 9504,
        "ok": 9486,
        "empty": 18,
        "error": 0,
        "layout_mapping_failed": 0,
        "image_content_without_text": 9,
        "readable_encrypted_source": 1607,
        "actualtext_position_warning": 618,
    }


def test_benchmark_references_and_frozen_split_are_reproducible(real_inputs):
    _, benchmark_root, corpus = real_inputs
    questions = benchmark_root / "financebench_open_source.jsonl"
    cases = load_benchmark(questions, corpus)
    assert len(cases) == 52 and len({c.doc_name for c in cases}) == 19
    references = [e for case in cases for e in case.evidence]
    assert len(references) == 59
    assert len({(e.doc_name, e.evidence_page_num) for e in references}) == 49
    documents = {d.doc_name: d for d in corpus.documents}
    pages = {}
    for evidence in references:
        if evidence.doc_name not in pages:
            pages[evidence.doc_name] = cache.load_cached(
                documents[evidence.doc_name], ExtractionConfig(), REPO / "data/cache/pages"
            )
        assert pages[evidence.doc_name][evidence.evidence_page_num].text.strip()
    directory = REPO / "configs/evaluation"
    dev = SplitManifest.model_validate_json((directory / "development.json").read_text())
    hold = SplitManifest.model_validate_json((directory / "holdout.json").read_text())
    policy = SplitPolicy.model_validate_json((directory / "split-policy.json").read_text())
    validate_split_pair(dev, hold)
    assert freeze_splits(
        tuple(reversed(cases)), policy, sha256_file(questions), corpus.source_fingerprint
    ) == (dev, hold)
    assert (
        dev.split_fingerprint == "e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431"
    )


def test_original_55_pdf_and_jsonl_hashes_remain_unchanged(real_inputs):
    pdf_root, benchmark_root, corpus = real_inputs
    names = {d.doc_name for d in corpus.documents}
    names.update(d.doc_names[0] for d in corpus.diagnostics if d.code == "duplicate_alias")
    pairs = [f"{name}:{sha256_file(pdf_root / (name + '.pdf'))}" for name in sorted(names)]
    assert len(pairs) == 55
    assert (
        hashlib.sha256("\n".join(pairs).encode()).hexdigest()
        == "7d8ca4d2d901038058ac345778ecb5898f20e04e6f5a0c97ffd344db41a776fe"
    )
    assert (
        sha256_file(benchmark_root / "financebench_open_source.jsonl")
        == "a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877"
    )
    assert (
        sha256_file(benchmark_root / "financebench_document_information.jsonl")
        == "1c69127783879de8cdadb159d2181f39bc3123b8e0ebf74031c3969d69189575"
    )
