"""Four-arm orchestration freezes paired pools and records explicit failures."""

import importlib
from types import SimpleNamespace

import pytest

from finsight.contracts import Chunk, QueryRequest, RetrievalCandidate
from finsight.contracts.retrieval_experiments import RetrievalExperimentConfig
from finsight.retrieval.reranking import LocalReranker
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


def experiment_module():
    assert importlib.util.find_spec("finsight.retrieval.experiments"), "Missing arm orchestration"
    return importlib.import_module("finsight.retrieval.experiments")


@pytest.fixture
def candidates(source, score):
    return tuple(
        RetrievalCandidate(
            chunk=Chunk(
                chunk_id=f"{i:064x}",
                document_id="synthetic",
                page_start=0,
                page_end=0,
                source_spans=[dict(page_index=0, char_start=0, char_end=10)],
                chunk_strategy="fixed",
                config_fingerprint="a" * 64,
                content=f"passage {i}",
                token_count=3,
            ),
            source=source,
            rank=i,
            score=score,
        )
        for i in range(1, 16)
    )


def test_four_arms_share_exactly_two_pools_and_rerank_the_whole_pool(candidates):
    module = experiment_module()
    from test_reranking import tiny_tokenizer

    def score(encodings, context):
        return [float(e.offsets[-2][1]) for e in encodings]

    # All passages tie except their original text lengths: "passage 15" beats "passage 1".
    reranker = LocalReranker(
        SimpleNamespace(tokenizer=tiny_tokenizer(), score=score, fingerprint=lambda: "b" * 64),
        RetrievalExperimentConfig().reranker,
    )
    calls = []

    def retrieve(strategy, request, context):
        calls.append((strategy, request))
        return module.DensePool(candidates=candidates, index_fingerprint="c" * 64)

    traces = module.run_arms(
        QueryRequest(question="AMD revenue?"),
        tuple(RetrievalExperimentConfig(arm=a) for a in "ABCD"),
        retrieve,
        reranker,
        lambda purpose: CallContext(purpose, 3, 1e20),
    )
    assert len(calls) == 2 and {s for s, _ in calls} == {"fixed", "semantic"}
    assert all(not r.document_ids and not r.company for _, r in calls)
    assert [t.status for t in traces] == ["complete"] * 4
    assert traces[0].pool_fingerprint == traces[2].pool_fingerprint
    assert traces[1].pool_fingerprint == traces[3].pool_fingerprint
    assert all(len(t.pool) == 15 and len(t.selected) == 5 for t in traces)
    assert traces[2].rerank_result is not None


def test_rerank_error_is_not_a_silent_baseline_fallback(candidates):
    module = experiment_module()

    class Failing:
        def rerank(self, *args):
            raise FinsightError("rerank_failed")

    traces = module.run_arms(
        QueryRequest(question="AMD revenue?"),
        tuple(RetrievalExperimentConfig(arm=a) for a in "ABCD"),
        lambda *args: module.DensePool(candidates=candidates, index_fingerprint="c" * 64),
        Failing(),
        lambda purpose: CallContext(purpose, 3, 1e20),
    )
    assert [t.status for t in traces] == ["complete", "complete", "error", "error"]
    assert not traces[2].selected and traces[2].error_code == "rerank_failed"


def test_uncertain_provider_failure_stops_later_dispatch(candidates):
    module = experiment_module()
    calls = []

    def retrieve(*args):
        calls.append(args)
        raise FinsightError("provider_timeout")

    traces = module.run_arms(
        QueryRequest(question="AMD revenue?"),
        tuple(RetrievalExperimentConfig(arm=a) for a in "ABCD"),
        retrieve,
        None,
        lambda purpose: CallContext(purpose, 3, 1e20),
    )
    assert len(calls) == 1
    assert all(t.status == "error" and not t.selected for t in traces)


def test_retrieval_metrics_join_document_and_page_without_duplicate_credit(candidates):
    assert importlib.util.find_spec("finsight.evaluation.retrieval"), (
        "Missing offline retrieval scorer"
    )
    scorer = importlib.import_module("finsight.evaluation.retrieval")
    result = scorer.retrieval_metrics(candidates, {("synthetic", 0), ("other", 0)})
    assert result["page_hit_at_5"] == 1
    assert result["gold_page_recall_at_5"] == 0.5
    assert result["mrr_at_15"] == 1
    assert result["candidate_pool_coverage"] == 0.5
    assert scorer.retrieval_metrics(candidates, {("wrong-document", 0)})["page_hit_at_5"] == 0
