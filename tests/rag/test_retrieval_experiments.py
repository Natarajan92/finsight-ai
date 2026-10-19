"""Paired experiments must share indexes without sharing spending allowances."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from finsight.contracts import BaselineConfig
from finsight.observability.budget import BudgetLedger
from finsight.runtime.errors import FinsightError


def experiment_config():
    assert importlib.util.find_spec("finsight.contracts.retrieval_experiments"), (
        "Missing experiment configuration"
    )
    return importlib.import_module("finsight.contracts.retrieval_experiments")


def test_paired_arms_share_indexes_and_have_distinct_run_identities():
    cls = experiment_config().RetrievalExperimentConfig
    arms = {arm: cls(arm=arm) for arm in "ABCD"}
    assert arms["A"].index_config().fingerprint() == BaselineConfig().fingerprint()
    assert arms["A"].index_config() == arms["C"].index_config()
    assert arms["B"].index_config() == arms["D"].index_config()
    assert arms["A"].index_config().fingerprint() != arms["B"].index_config().fingerprint()
    assert len({c.fingerprint() for c in arms.values()}) == 4
    assert [(c.chunk_strategy, c.rerank) for c in arms.values()] == [
        ("fixed", False),
        ("semantic", False),
        ("fixed", True),
        ("semantic", True),
    ]
    with pytest.raises(ValueError):
        cls(phase3_usd="0.76")


def test_phase3_atomic_cap_preserves_prior_unknown_phase2_spend(tmp_path):
    ledger = BudgetLedger.initialize(
        tmp_path / "budget.db", BaselineConfig().budget_id, anchor_path=tmp_path / "anchor.json"
    )
    prior = ledger.reserve("prior", "nebius", "model", Decimal("0.70"), 2)
    ledger.mark_dispatched(prior.reservation_id)
    ledger.settle(prior.reservation_id, None)

    def reserve(identity):
        try:
            ledger.reserve(identity, "nebius", "model", Decimal("0.40"), 3)
            return "reserved"
        except FinsightError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, ["one", "two"]))
    assert sorted(results) == ["budget_exceeded", "reserved"]
    assert ledger.snapshot().reserved_usd == Decimal("1.10")
    assert ledger.snapshot().phase2_available_usd == Decimal("0.05")
    assert ledger.phase_available(3) == Decimal("0.35")
    with pytest.raises(FinsightError, match="budget_exceeded"):
        ledger.reserve(
            "lower-cap", "nebius", "model", Decimal("0.01"), 3, phase3_usd=Decimal("0.40")
        )


def test_phase3_and_global_caps_both_apply(tmp_path):
    ledger = BudgetLedger.initialize(
        tmp_path / "budget.db", BaselineConfig().budget_id, anchor_path=tmp_path / "anchor.json"
    )
    ledger.reserve("other-phase", "nebius", "model", Decimal("3.50"), 4)
    ledger.reserve("phase3", "nebius", "model", Decimal("0.40"), 3)
    with pytest.raises(FinsightError, match="budget_exceeded"):
        ledger.reserve("global-over", "nebius", "model", Decimal("0.11"), 3)
    assert ledger.phase_available(3) == Decimal("0.35")
    assert ledger.snapshot().available_usd == Decimal("0.10")
