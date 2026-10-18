"""Every physical send must have a durable reservation and a current price."""

import importlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from finsight.contracts.runtime import ProviderUsage
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


@pytest.fixture
def setup_dispatch(tmp_path):
    assert importlib.util.find_spec("finsight.observability.dispatch"), "Missing guarded dispatch"
    c = importlib.import_module("finsight.contracts.budget")
    b = importlib.import_module("finsight.observability.budget")
    d = importlib.import_module("finsight.observability.dispatch")
    now = datetime.now(UTC)
    rates = c.RateBook(
        cards=[
            dict(
                provider="anthropic",
                model="claude-sonnet-5",
                service_tier="default",
                input_per_million="1",
                output_per_million="5",
                source_url="https://platform.claude.com/docs/en/about-claude/pricing",
                verified_at=now,
            ),
            dict(
                provider="nebius",
                model="Qwen/Qwen3-Embedding-8B",
                service_tier="default",
                input_per_million="1",
                output_per_million="0",
                source_url="https://nebius.com/token-factory/prices",
                verified_at=now,
            ),
        ]
    )
    ledger = b.BudgetLedger.initialize(tmp_path / "budget.sqlite3", "finsight-testing-2026-10-18")
    dispatch = d.GuardedDispatcher(ledger, rates)
    estimate = c.CallEstimate(
        request_id="call",
        provider="anthropic",
        model="claude-sonnet-5",
        rate_fingerprint=rates.fingerprint(),
        input_tokens=1000,
        max_output_tokens=100,
        maximum_usd="0.0015",
        service_tier="default",
    )
    return dispatch, estimate, CallContext("run", 2, 45, clock=lambda: 0), rates


def test_known_usage_settles_before_downstream_parse(setup_dispatch):
    dispatch, estimate, context, _ = setup_dispatch
    raw = object()
    usage = ProviderUsage(
        provider="anthropic",
        model=estimate.model,
        input_tokens=500,
        output_tokens=10,
        cache_read_tokens=0,
        cache_write_tokens=0,
        usage_known=True,
    )
    assert dispatch.execute(estimate, lambda: raw, lambda _: usage, context) is raw
    assert dispatch.ledger.snapshot().accounted_usd == Decimal("0.00055")
    assert dispatch.ledger.snapshot().reserved_usd == 0
    assert dispatch.attempts[0].usage.cost_basis == "usage_priced"
    with pytest.raises(FinsightError, match="duplicate_request"):
        dispatch.execute(estimate, lambda: pytest.fail("second dispatch"), lambda _: None, context)


def test_timeout_does_not_retry_and_retains_unknown_usage(setup_dispatch):
    dispatch, estimate, context, _ = setup_dispatch
    calls = []

    def send():
        calls.append(1)
        raise TimeoutError("synthetic credential must not be exposed")

    with pytest.raises(FinsightError, match="provider_timeout"):
        dispatch.execute(estimate, send, lambda _: None, context)
    assert calls == [1]
    assert dispatch.ledger.snapshot().reserved_usd == Decimal("0.0015")
    assert dispatch.attempts[0].usage is None


def test_expired_or_missing_rate_blocks_send(setup_dispatch):
    dispatch, estimate, context, rates = setup_dispatch
    stale = rates.model_copy(
        update={
            "cards": tuple(
                card.model_copy(update={"verified_at": datetime.now(UTC) - timedelta(days=2)})
                for card in rates.cards
            )
        }
    )
    dispatch.rates = stale
    with pytest.raises(FinsightError, match="rate_expired"):
        dispatch.execute(estimate, lambda: pytest.fail("stale dispatch"), lambda _: None, context)
    dispatch.rates = rates
    wrong = estimate.model_copy(update={"model": "missing-model"})
    with pytest.raises(FinsightError, match="rate_unavailable"):
        dispatch.execute(wrong, lambda: pytest.fail("missing rate"), lambda _: None, context)
    assert dispatch.ledger.snapshot().reserved_usd == 0


def test_retry_reserves_again_and_stops_at_two_attempts(setup_dispatch):
    dispatch, estimate, context, _ = setup_dispatch
    calls = []

    class RetryResponse(Exception):
        status_code = 503

    def send():
        calls.append(1)
        raise RetryResponse()

    with pytest.raises(FinsightError, match="provider_status"):
        dispatch.execute(estimate, send, lambda _: None, context)
    assert len(calls) == 2
    assert len(dispatch.attempts) == 2
    assert dispatch.attempts[0].request_id != dispatch.attempts[1].request_id
    # Even an explicit rejection retains money unless cost is established.
    assert dispatch.ledger.snapshot().reserved_usd == Decimal("0.003")


def test_deadline_prevents_next_dispatch(setup_dispatch):
    dispatch, estimate, _, _ = setup_dispatch
    context = CallContext("run", 2, 0, clock=lambda: 1)
    with pytest.raises(FinsightError, match="deadline_exceeded"):
        dispatch.execute(estimate, lambda: pytest.fail("expired send"), lambda _: None, context)
    assert dispatch.ledger.snapshot().reserved_usd == 0


def test_underestimated_or_mismatched_price_blocks_send(setup_dispatch):
    dispatch, estimate, context, _ = setup_dispatch
    for changes in [{"maximum_usd": Decimal("0.0001")}, {"rate_fingerprint": "a" * 64}]:
        with pytest.raises(FinsightError, match="rate_integrity"):
            dispatch.execute(
                estimate.model_copy(update=changes),
                lambda: pytest.fail("bad estimate"),
                lambda _: None,
                context,
            )


def test_unknown_token_categories_do_not_free_reserved_money(setup_dispatch):
    dispatch, estimate, context, _ = setup_dispatch
    usage = ProviderUsage(
        provider="anthropic",
        model=estimate.model,
        input_tokens=20,
        cost_usd="0.00001",
        cost_basis="usage_priced",
    )
    dispatch.execute(estimate, lambda: object(), lambda _: usage, context)
    assert dispatch.ledger.snapshot().reserved_usd == Decimal("0.0015")
    assert dispatch.attempts[0].usage.cost_usd is None
    assert dispatch.attempts[0].usage.output_tokens is None


def test_denied_budget_and_deleted_database_never_send(setup_dispatch):
    dispatch, estimate, context, _ = setup_dispatch
    dispatch.ledger.reserve("exhaust", "nebius", "Qwen/Qwen3-Embedding-8B", Decimal("0.75"), 2)
    with pytest.raises(FinsightError, match="budget_exceeded"):
        dispatch.execute(estimate, lambda: pytest.fail("denied send"), lambda _: None, context)
    dispatch.ledger.path.unlink()
    with pytest.raises(FinsightError, match="budget_unavailable"):
        dispatch.execute(estimate, lambda: pytest.fail("missing db send"), lambda _: None, context)


def test_deadline_prevents_retry_after_first_response(setup_dispatch):
    dispatch, estimate, _, _ = setup_dispatch
    clock = [0.0]
    context = CallContext("run", 2, 10, clock=lambda: clock[0])

    class Rejected(Exception):
        status_code = 429

    calls = []

    def send():
        calls.append(1)
        clock[0] = 11
        raise Rejected()

    with pytest.raises(FinsightError, match="deadline_exceeded"):
        dispatch.execute(estimate, send, lambda _: None, context)
    assert len(calls) == 1
