"""Installed commands work outside the repo and keep paid execution explicit."""

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def cli():
    assert importlib.util.find_spec("finsight.cli"), "Missing baseline CLI"
    return importlib.import_module("finsight.cli")


def test_installed_synthetic_smoke_runs_from_empty_cwd(tmp_path):
    script = Path(sys.executable).parent / (
        "finsight-rag.exe" if os.name == "nt" else "finsight-rag"
    )
    assert script.is_file(), "Missing installed baseline CLI"
    result = subprocess.run(
        [str(script), "smoke", "--synthetic"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["check"] == "synthetic_rag_roundtrip"
    assert report["provider_network_calls"] == 0


def test_budget_init_never_overwrites_existing_ledger(tmp_path, capsys):
    path = tmp_path / "budget.sqlite3"
    assert cli().main(["budget-init", "--ledger", str(path)]) == 0
    capsys.readouterr()
    assert cli().main(["budget-init", "--ledger", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "budget_exists"


def test_ask_without_paid_opt_in_fails_before_provider_setup(tmp_path, capsys):
    config = Path(__file__).resolve().parents[2] / "configs/runtime/phase-2-baseline.json"
    code = cli().main(["ask", "--config", str(config), "--question", "AMD revenue?"])
    assert code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["answer"]["error"]["code"] == "paid_not_authorized"
    assert result["trace_id"] is None


def test_factory_without_paid_opt_in_never_creates_clients():
    assert importlib.util.find_spec("finsight.runtime.factory"), "Missing application factory"
    from finsight.config import Settings
    from finsight.contracts import BaselineConfig
    from finsight.runtime.errors import FinsightError
    from finsight.runtime.factory import create_application

    with pytest.raises(FinsightError, match="paid_not_authorized"):
        create_application(Settings(_env_file=None), BaselineConfig())


def test_preflight_is_keyless_and_reports_a_budget_conflict(
    index_setup, synthetic_rates, tmp_path, monkeypatch
):
    import finsight.runtime.factory as factory
    from finsight.config import Settings
    from finsight.observability.budget import BudgetLedger

    _, corpus, pages, config, _, _, _, tokenizer = index_setup
    rates_path = tmp_path / "rates.json"
    rates_path.write_text(synthetic_rates.model_dump_json(), encoding="utf-8")
    ledger_path = tmp_path / "budget.sqlite3"
    BudgetLedger.initialize(ledger_path, config.budget_id)
    settings = Settings(
        _env_file=None,
        rates_path=rates_path,
        ledger_path=ledger_path,
        embedding_cache_root=tmp_path / "embeddings",
    )
    monkeypatch.setattr(factory, "local_assets", lambda *args: (corpus, pages, tokenizer))
    report = factory.preflight(settings, config)
    assert report["status"] == "ready" and report["provider_network_calls"] == 0
    assert report["documents"] == 2 and report["chunks"] > 0
    assert (
        factory.preflight(
            settings,
            config.model_copy(update={"phase2_usd": __import__("decimal").Decimal("0.001")}),
        )["status"]
        == "budget_conflict"
    )
