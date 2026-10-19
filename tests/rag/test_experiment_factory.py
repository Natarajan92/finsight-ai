"""Real synthetic PDFs/Chroma and the production budgeted provider boundary."""

import importlib
import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from finsight.config import Settings
from finsight.contracts import QueryRequest
from finsight.retrieval.reranking import LocalReranker
from finsight.runtime.errors import FinsightError


@pytest.fixture
def lab(index_setup, embedding_setup, tmp_path):
    assert importlib.util.find_spec("finsight.runtime.experiment_factory"), (
        "Missing experiment facade"
    )
    module = importlib.import_module("finsight.runtime.experiment_factory")
    from test_reranking import tiny_tokenizer

    _, corpus, pages, config, _, _, _, tokenizer = index_setup
    backend, cache, dispatcher, calls, responses = embedding_setup
    rates = tmp_path / "rates.json"
    rates.write_text(dispatcher.rates.model_dump_json())
    settings = Settings(
        _env_file=None,
        source_pdf_dir=pages.pdf_root,
        page_cache_root=pages.cache_root,
        index_root=tmp_path / "indexes",
        trace_root=tmp_path / "traces",
        embedding_cache_root=cache.root,
        ledger_path=dispatcher.ledger.path,
        budget_anchor_path=dispatcher.ledger.anchor,
        rates_path=rates,
        tokenizer_dir=tmp_path / "tokenizer",
    )
    scorer = LocalReranker(
        SimpleNamespace(
            tokenizer=tiny_tokenizer(),
            fingerprint=lambda: "b" * 64,
            score=lambda encodings, ctx: [0.0] * len(encodings),
        ),
        module.RetrievalExperimentConfig().reranker,
        tmp_path / "rerank-cache",
    )
    session = module.ExperimentLab(
        settings,
        corpus,
        pages,
        tokenizer,
        baseline=config,
        backend=replace(backend, config=config),
        dispatcher=dispatcher,
        reranker=scorer,
    )
    yield session, calls, responses, dispatcher.ledger
    session.close()


def prepare_indexes(session):
    for _ in range(20):
        if not session.semantic_progress()["missing_unique_inputs"]:
            break
        session.embed_semantic(allow_paid=True)
    else:
        raise AssertionError("Synthetic preparation did not finish")
    session.prepare_semantic()
    for arm in "AB":
        for _ in range(20):
            if not session.chunk_progress(arm)["missing_unique_inputs"]:
                break
            session.embed_chunks(arm, allow_paid=True)
        else:
            raise AssertionError("Synthetic chunk embeddings did not finish")
        session.build_index(arm)


def test_missing_inputs_cannot_purchase_through_default_or_index_stage(lab):
    session, calls, _, ledger = lab
    assert session.preflight("semantic")["provider_network_calls"] == 0
    with pytest.raises(FinsightError, match="paid_not_authorized"):
        session.embed_semantic()
    with pytest.raises(FinsightError, match="experiment_embeddings_missing"):
        session.build_index("A")
    assert not calls and ledger.snapshot().reserved_usd == 0


def test_scoped_indexes_four_arms_and_replay_reuse_paid_inputs(lab):
    session, calls, _, ledger = lab
    prepare_indexes(session)
    assert session.index_path("A") == session.index_path("C")
    assert session.index_path("B") == session.index_path("D")
    assert session.index_path("A") != session.index_path("B")
    count = len(calls)
    request = QueryRequest(question="What was AMD revenue?")
    traces = session.run_arms(request, allow_paid=True)
    assert all(t.status == "complete" for t in traces)
    assert len(calls) == count + 1  # One shared query vector across both index strategies.
    assert traces[0].pool_fingerprint == traces[2].pool_fingerprint
    assert traces[1].pool_fingerprint == traces[3].pool_fingerprint
    count = len(calls)
    replay = session.run_arms(request)
    assert len(calls) == count and all(t.status == "complete" for t in replay)
    assert [t.selected for t in replay] == [t.selected for t in traces]
    assert all(t.pool_replay for t in replay)
    assert ledger.snapshot().phase2_available_usd == Decimal("0.75")
    path = next((session.trace_root / "pools").rglob("pool.json"))
    raw = json.loads(path.read_text())
    raw["identity"]["request"] = "tampered"
    path.write_text(json.dumps(raw))
    changed = session.run_arms(request, allow_paid=True)
    assert any(t.error_code == "experiment_pool_integrity" for t in changed)
    assert len(calls) == count


def test_uncertain_query_is_not_automatically_repurchased(lab):
    session, calls, responses, ledger = lab
    prepare_indexes(session)
    count = len(calls)
    responses.append(httpx.ReadTimeout("synthetic timeout"))
    request = QueryRequest(question="What was AMD revenue?")
    traces = session.run_arms(request, allow_paid=True)
    assert len(calls) == count + 1 and all(t.status == "error" for t in traces)
    reserved = ledger.snapshot().reserved_usd
    assert reserved > 0
    again = session.run_arms(request, allow_paid=True)
    assert len(calls) == count + 1 and any(t.error_code == "experiment_interrupted" for t in again)
    assert ledger.snapshot().reserved_usd == reserved


def test_expansion_requires_accepted_baseline_before_dispatch(lab, tmp_path):
    from finsight.evaluation.retrieval import run_development_comparison

    session, calls, _, _ = lab
    with pytest.raises(FinsightError, match="baseline_acceptance_pending"):
        run_development_comparison(
            session, tmp_path / "questions", tmp_path / "splits", allow_paid=True
        )
    assert not calls


def test_manual_answers_are_off_by_default_and_require_amd_scope(lab):
    session, calls, _, _ = lab
    with pytest.raises(FinsightError, match="experiment_pilot_scope"):
        session.ask_pilot(QueryRequest(question="AMD revenue?"), "A", allow_paid=True)
    assert not calls
