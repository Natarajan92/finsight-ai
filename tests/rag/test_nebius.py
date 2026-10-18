"""Mocked HTTP response tests retain usage before rejecting unusable vectors."""

import math
from decimal import Decimal

import httpx
import pytest

from finsight.runtime.errors import FinsightError


def test_vectors_cached_unit_normalized_with_explicit_request(embedding_setup):
    backend, _, dispatch, calls, _ = embedding_setup
    first = backend.embed_documents(["same text", "second text"])
    assert first == backend.embed_documents(["same text", "second text"])
    assert len(calls) == 1
    request, body = calls[0]
    assert str(request.url) == "https://api.tokenfactory.nebius.com/v1/embeddings"
    assert body == {
        "model": "Qwen/Qwen3-Embedding-8B",
        "input": ["same text", "second text"],
        "dimensions": 3,
        "encoding_format": "float",
        "service_tier": "default",
    }
    assert request.extensions["timeout"]["read"] == 20
    assert all(math.isclose(sum(v * v for v in vector), 1) for vector in first)
    assert dispatch.ledger.snapshot().reserved_usd == Decimal("0")


def test_query_prefix_is_frozen_and_not_applied_to_documents(embedding_setup):
    backend, _, _, calls, _ = embedding_setup
    backend.embed_query("Revenue?")
    assert calls[0][1]["input"] == [
        "Instruct: Given a financial question, retrieve passages from company filings "
        "that answer the question.\nQuery:Revenue?"
    ]
    backend.embed_documents(["Revenue?"])
    assert calls[1][1]["input"] == ["Revenue?"]


def test_response_indices_are_reordered(embedding_setup):
    backend, _, _, _, responses = embedding_setup
    responses.append(
        {
            "model": backend.config.embedding_model,
            "data": [{"index": 1, "embedding": [0, 0, 1]}, {"index": 0, "embedding": [1, 0, 0]}],
            "usage": {"prompt_tokens": 2},
        }
    )
    assert backend.embed_documents(["a", "b"]) == [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]


@pytest.mark.parametrize(
    "data",
    [
        [{"index": 0, "embedding": [1, 0, 0]}, {"index": 0, "embedding": [1, 0, 0]}],
        [],
        [{"index": 0, "embedding": [1, 0]}],
        [{"index": 0, "embedding": [0, 0, 0]}],
        [{"index": 0, "embedding": [float("nan"), 0, 1]}],
        [{"index": 0, "embedding": [float("inf"), 0, 1]}],
    ],
)
def test_malformed_vectors_never_cached_but_usage_retained(embedding_setup, data):
    backend, cache, dispatch, _, responses = embedding_setup
    # HTTPX JSON encoding forbids NaN; inject these after decoding instead.
    if any(not math.isfinite(v) for row in data for v in row["embedding"]):
        from finsight.indexing.embedding_cache import normalize_vector

        with pytest.raises(FinsightError, match="embedding_shape"):
            normalize_vector(data[0]["embedding"], 3)
        return
    responses.append(
        {"model": backend.config.embedding_model, "data": data, "usage": {"prompt_tokens": 1}}
    )
    with pytest.raises(FinsightError, match="embedding_shape"):
        backend.embed_documents(["one"])
    assert cache.get(cache.key("one", role="document")) is None
    assert dispatch.attempts[0].usage.input_tokens == 1
    assert dispatch.ledger.snapshot().reserved_usd == 0


def test_successful_batches_survive_later_timeout_and_resume(embedding_setup):
    backend, _, dispatch, calls, responses = embedding_setup
    inputs = [f"doc{i}" for i in range(17)]
    responses.extend(
        [
            {
                "model": backend.config.embedding_model,
                "data": [{"index": i, "embedding": [1, 0, 0]} for i in range(16)],
                "usage": {"prompt_tokens": 64},
            },
            httpx.ReadTimeout("synthetic timeout"),
        ]
    )
    with pytest.raises(FinsightError, match="provider_timeout"):
        backend.embed_documents(inputs)
    assert len(calls) == 2
    assert len(backend.embed_documents(inputs)) == 17
    assert len(calls) == 3
    assert len(calls[-1][1]["input"]) == 1
    assert dispatch.ledger.snapshot().reserved_usd > 0


def test_unauthorized_batch_never_sends(embedding_setup):
    backend, _, dispatch, calls, _ = embedding_setup
    dispatch.ledger.reserve("exhaust", "nebius", backend.config.embedding_model, Decimal("0.75"), 2)
    with pytest.raises(FinsightError, match="budget_exceeded"):
        backend.embed_documents(["one"])
    assert not calls


def test_redirect_is_not_followed_or_retried(embedding_setup):
    from dataclasses import replace

    backend, _, dispatch, _, _ = embedding_setup
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://example.invalid/embeddings"})

    with httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True) as client:
        with pytest.raises(FinsightError, match="provider_status"):
            replace(backend, client=client).embed_documents(["one"])
    assert len(requests) == 1
    assert len(dispatch.attempts) == 1


def test_live_dimension_profile_and_immutable_run_binding(embedding_setup, tmp_path):
    from dataclasses import replace

    from finsight.indexing.embedding_cache import EmbeddingCache
    from finsight.runtime.ports import CallContext

    backend, _, _, _, responses = embedding_setup
    config = backend.config.model_copy(update={"embedding_dimension": 4096})
    live = replace(
        backend, config=config, cache=EmbeddingCache(tmp_path / "live-dimension", config)
    )
    responses.append(
        {
            "model": config.embedding_model,
            "data": [{"index": 0, "embedding": [1.0] * 4096}],
            "usage": {"prompt_tokens": 1},
        }
    )
    assert len(live.embed_documents(["one"])[0]) == 4096
    assert live.for_run(CallContext("other", 2, 100)).context.run_id == "other"
    assert live.context.run_id == "run"
