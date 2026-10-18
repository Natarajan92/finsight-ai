"""Explicit local/paid acceptance. Completed campaigns replay without new purchases."""

import os
from pathlib import Path

import pytest

from finsight.config import Settings
from finsight.contracts import BaselineConfig
from finsight.contracts.ingestion import CorpusManifest
from finsight.ingestion.fingerprints import sha256_file
from finsight.ingestion.pages import CachedPageRepository

pytestmark = pytest.mark.integration
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def real_rag_settings():
    root = os.environ.get("FINSIGHT_SOURCE_PDF_DIR")
    benchmark = os.environ.get("FINSIGHT_BENCHMARK_DIR")
    if not root or not benchmark:
        if os.environ.get("FINSIGHT_RAG_PAID_TESTS") == "1":
            pytest.fail("Paid opt-in needs explicit source/benchmark paths")
        pytest.skip("Set explicit FinanceBench source/benchmark paths for RAG acceptance")
    return Settings(
        _env_file=REPO / ".env",
        source_pdf_dir=Path(root),
        manifest_path=REPO / "data/manifests/financebench-selected.json",
        page_cache_root=REPO / "data/cache/pages",
        tokenizer_dir=REPO / "data/cache/tokenizer/qwen3-embedding-8b",
        embedding_cache_root=REPO / "data/cache/embeddings",
        index_root=REPO / "data/indexes",
        rates_path=REPO / "data/cache/budget/rates.json",
        ledger_path=REPO / "data/cache/budget/testing.sqlite3",
        trace_root=REPO / "results/traces",
    ), Path(benchmark)


def test_real_sources_and_phase1_caches_remain_unchanged(real_rag_settings):
    settings, _ = real_rag_settings
    corpus = CorpusManifest.model_validate_json(settings.manifest_path.read_text(encoding="utf-8"))
    assert len(corpus.documents) == 53 and sum(d.page_count for d in corpus.documents) == 9504
    assert corpus.source_fingerprint == BaselineConfig().source_fingerprint
    cache_before = {p.name: sha256_file(p) for p in settings.page_cache_root.glob("*.json")}
    repo = CachedPageRepository(corpus, settings.source_pdf_dir, settings.page_cache_root)
    for document in corpus.documents:
        repo.validate(document.document_id)
    assert cache_before == {p.name: sha256_file(p) for p in settings.page_cache_root.glob("*.json")}


def test_completed_real_index_has_expected_source_windows(real_rag_settings):
    from finsight.indexing.builder import open_index
    from finsight.runtime.factory import local_assets

    settings, _ = real_rag_settings
    config = BaselineConfig()
    root = settings.index_root / config.fingerprint()
    if not (root / "manifest.json").is_file():
        if os.environ.get("FINSIGHT_RAG_PAID_TESTS") == "1":
            pytest.fail("Paid opt-in requires the completed, preflighted index")
        pytest.skip("Real index has not been built; source-only checks can still run")
    corpus, pages, tokenizer = local_assets(settings, config)

    class NoSend:
        def for_run(self, context):
            return self

        def embed_query(self, text):
            raise AssertionError("Index validation must be local")

    retriever = open_index(
        root, config, corpus, pages=pages, embeddings=NoSend(), tokenizer=tokenizer
    )
    try:
        assert retriever.manifest.chunk_count == len(retriever.catalog.chunks) > 0
        assert retriever.manifest.dimension == 4096
    finally:
        retriever.store.client.close()


def test_single_budgeted_development_campaign(real_rag_settings):
    if os.environ.get("FINSIGHT_RAG_PAID_TESTS") != "1":
        pytest.skip(
            "Provider campaign requires FINSIGHT_RAG_PAID_TESTS=1; integration alone cannot spend"
        )
    from finsight.evaluation.smoke import run_development_campaign
    from finsight.runtime.errors import FinsightError

    settings, benchmark = real_rag_settings
    try:
        result = run_development_campaign(
            settings,
            BaselineConfig(),
            benchmark / "financebench_open_source.jsonl",
            REPO / "configs/evaluation",
            allow_paid=True,
        )
    except FinsightError as exc:
        pytest.fail("Provider acceptance blocked: " + exc.code)
    assert len(result["runs"]) == 4
    assert result["runs"][-1]["status"] == "insufficient_evidence"
    assert all(row["status"] != "error" for row in result["runs"])
    assert any(row["status"] in {"answered", "partial"} for row in result["runs"][:3])
