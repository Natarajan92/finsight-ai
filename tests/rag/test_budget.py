"""Spend authorization survives concurrency, corruption and restarts."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from finsight.runtime.errors import FinsightError

BUDGET_ID = "finsight-testing-2026-10-18"


def ledger_type():
    assert importlib.util.find_spec("finsight.observability.budget"), "Missing durable ledger"
    return importlib.import_module("finsight.observability.budget").BudgetLedger


@pytest.fixture
def ledger(tmp_path):
    return ledger_type().initialize(tmp_path / "testing.sqlite3", BUDGET_ID)


def reserve(ledger, identity="one", amount="0.74", phase=2):
    return ledger.reserve(identity, "anthropic", "claude-sonnet-5", Decimal(amount), phase)


def test_phase_and_global_limits_persist(ledger):
    reserve(ledger)
    with pytest.raises(FinsightError, match="budget_exceeded"):
        reserve(ledger, "two", "0.02")
    reopened = ledger_type().open(ledger.path, BUDGET_ID)
    assert reopened.snapshot().reserved_usd == Decimal("0.74")
    reserve(reopened, "phase3", "3.26", 3)
    with pytest.raises(FinsightError, match="budget_exceeded"):
        reserve(reopened, "last", "0.000001", 3)
    assert reopened.snapshot().available_usd == 0
    assert reopened.snapshot().reserve_usd == Decimal("1")


def test_timeout_retains_full_reservation_after_restart(ledger):
    r = reserve(ledger)
    ledger.mark_dispatched(r.reservation_id)
    ledger.settle(r.reservation_id, None)
    reopened = ledger_type().open(ledger.path, BUDGET_ID)
    assert reopened.snapshot().reserved_usd == Decimal("0.74")
    assert reopened.snapshot().accounted_usd == 0


def test_two_connections_cannot_overreserve(ledger):
    def attempt(identity):
        other = ledger_type().open(ledger.path, BUDGET_ID)
        try:
            reserve(other, identity, "0.5")
            return True
        except FinsightError as error:
            assert error.code == "budget_exceeded"
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ["a", "b"])) == [False, True]
    assert ledger.snapshot().reserved_usd == Decimal("0.5")


def test_duplicate_request_cannot_dispatch_twice(ledger):
    r = reserve(ledger)
    ledger.mark_dispatched(r.reservation_id)
    with pytest.raises(FinsightError, match="duplicate_request"):
        ledger.mark_dispatched(r.reservation_id)
    with pytest.raises(FinsightError, match="duplicate_request"):
        reserve(ledger)


def test_missing_or_corrupt_ledger_blocks_send(ledger):
    path = ledger.path
    with pytest.raises(FinsightError, match="budget_exists"):
        ledger_type().initialize(path, BUDGET_ID)
    path.unlink()
    with pytest.raises(FinsightError, match="budget_unavailable"):
        ledger_type().open(path, BUDGET_ID)
    with pytest.raises(FinsightError, match="budget_exists"):
        ledger_type().initialize(path, BUDGET_ID)
    path.write_bytes(b"corrupt database")
    with pytest.raises(FinsightError, match="budget_integrity"):
        ledger_type().open(path, BUDGET_ID)


def test_actual_cost_over_reservation_is_recorded_not_clamped(ledger):
    r = reserve(ledger, amount="0.1")
    ledger.mark_dispatched(r.reservation_id)
    ledger.settle(r.reservation_id, Decimal("0.8"))
    assert ledger.snapshot().accounted_usd == Decimal("0.8")
    assert ledger.snapshot().reserved_usd == 0
    assert ledger.snapshot().phase2_available_usd == 0
    with pytest.raises(FinsightError, match="budget_exceeded"):
        reserve(ledger, "later", "0.001")


def test_round_up_and_invalid_state_or_identity_rejected(ledger):
    r = reserve(ledger, amount="0.0000001")
    assert r.maximum_usd == Decimal("0.000001")
    with pytest.raises(FinsightError, match="budget_state"):
        ledger.settle(r.reservation_id, Decimal("0"))
    with pytest.raises(FinsightError, match="budget_identity"):
        ledger_type().open(ledger.path, "different")
    with pytest.raises((ValueError, FinsightError)):
        reserve(ledger, "bad", "NaN")
