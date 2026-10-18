"""The foundation runs without data/services and keeps configured secrets private."""

import ast
import importlib
import importlib.util
import io
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from finsight import config


def settings_type():
    result = getattr(config, "Settings", None)
    assert result is not None, "Missing approved Settings model"
    return result


@pytest.fixture(autouse=True)
def clean_settings_env(monkeypatch):
    for name in os.environ:
        if name.startswith("FINSIGHT_"):
            monkeypatch.delenv(name)


def test_settings_boot_without_credentials_or_source_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = settings_type()(_env_file=None)
    assert settings.api_key is None
    assert settings.source_pdf_dir == Path("source-data/pdfs")
    assert settings.log_level == "INFO"
    assert not settings.source_pdf_dir.exists()


def test_environment_overrides_dotenv_and_masks_key(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("FINSIGHT_LOG_LEVEL=WARNING\nUNRELATED_ENTRY=ignored\n", encoding="utf-8")
    monkeypatch.setenv("FINSIGHT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("FINSIGHT_API_KEY", "synthetic-secret-value")
    settings = settings_type()(_env_file=dotenv)
    assert settings.log_level == "DEBUG"
    assert "synthetic-secret-value" not in repr(settings)
    assert "synthetic-secret-value" not in settings.model_dump_json()


def test_invalid_log_level_fails_at_configuration_boundary():
    with pytest.raises(ValidationError):
        settings_type()(_env_file=None, log_level="EVERYTHING")


def logging_configurer():
    name = "finsight.observability.logging"
    assert importlib.util.find_spec("finsight.observability") is not None, "Missing observability"
    assert importlib.util.find_spec(name) is not None, "Missing logging module"
    return importlib.import_module(name).configure_logging


def test_logging_redacts_formatted_args_and_exception_traces_without_propagation():
    settings = settings_type()(_env_file=None, api_key="synthetic-secret-value")
    output, root_output = io.StringIO(), io.StringIO()
    root_handler = logging.StreamHandler(root_output)
    logging.getLogger().addHandler(root_handler)
    try:
        logger = logging_configurer()(settings, stream=output)
        logger.warning("key=%s", "synthetic-secret-value")
        try:
            raise ValueError("provider echoed synthetic-secret-value")
        except ValueError:
            logging.getLogger("finsight.generation").exception("Provider failure")
        text = output.getvalue()
        assert "synthetic-secret-value" not in text
        assert "[REDACTED]" in text
        assert "ValueError: provider echoed [REDACTED]" in text
        assert root_output.getvalue() == ""
    finally:
        logging.getLogger().removeHandler(root_handler)


def test_reconfiguring_logging_does_not_duplicate_messages():
    settings = settings_type()(_env_file=None)
    output = io.StringIO()
    configure = logging_configurer()
    configure(settings, stream=output)
    logger = configure(settings, stream=output)
    logger.info("one message")
    assert output.getvalue().count("one message") == 1


def test_malformed_log_format_cannot_leak_raw_secret_arguments(capsys):
    settings = settings_type()(_env_file=None, api_key="synthetic-secret-value")
    logger = logging_configurer()(settings, stream=io.StringIO())
    original_raise_exceptions = logging.raiseExceptions
    logger.warning("Provider failed", "synthetic-secret-value")
    diagnostic = capsys.readouterr().err
    assert "synthetic-secret-value" not in diagnostic
    assert "FinSight logging output failed" in diagnostic
    assert logging.raiseExceptions == original_raise_exceptions


def test_failed_log_stream_cannot_leak_secret_record_or_exception(capsys):
    class FailingStream:
        def write(self, text):
            raise OSError("sink rejected synthetic-secret-value")

        def flush(self):
            pass

    settings = settings_type()(_env_file=None, api_key="synthetic-secret-value")
    logger = logging_configurer()(settings, stream=FailingStream())
    logger.warning("Provider key=%s", "synthetic-secret-value")
    diagnostic = capsys.readouterr().err
    assert "synthetic-secret-value" not in diagnostic
    assert "FinSight logging output failed" in diagnostic


def test_synthetic_smoke_without_network_reports_page_zero_and_unknown_cost():
    assert importlib.util.find_spec("finsight.smoke") is not None, "Missing synthetic smoke"
    smoke = importlib.import_module("finsight.smoke")
    assert smoke.run_smoke() == {
        "check": "synthetic_contract_roundtrip",
        "status": "passed",
        "page_index": 0,
        "cost_usd": "unknown",
    }


def test_clean_process_runtime_imports_do_not_load_evaluation(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import finsight.contracts, finsight.config; import sys; "
            "assert not any(n.startswith('finsight.evaluation') for n in sys.modules)",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_runtime_source_has_no_evaluation_imports():
    root = Path(__file__).resolve().parents[1] / "src" / "finsight"
    for path in root.rglob("*.py"):
        if "evaluation" in path.relative_to(root).parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or "", *(a.name for a in node.names)]
            else:
                continue
            assert all("evaluation" not in name.split(".") for name in modules), path


def test_installed_smoke_entrypoint_runs_from_an_empty_directory(tmp_path):
    script = Path(sys.executable).parent / (
        "finsight-smoke.exe" if os.name == "nt" else "finsight-smoke"
    )
    assert script.exists(), "Missing installed smoke entry point"
    result = subprocess.run(
        [str(script)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["check"] == "synthetic_contract_roundtrip"
