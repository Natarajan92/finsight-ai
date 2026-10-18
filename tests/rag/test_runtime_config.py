"""Configuration must bound spending and keep runtime imports credential-free."""

import importlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from finsight import contracts
from finsight.config import Settings


def config_type():
    result = getattr(contracts, "BaselineConfig", None)
    assert result is not None, "Missing baseline runtime configuration"
    return result


def test_configuration_bounds_and_fingerprint():
    config = config_type()()
    assert (config.chunk_tokens, config.overlap_tokens) == (400, 60)
    assert (config.candidate_count, config.top_k, config.context_tokens) == (15, 5, 3500)
    assert (config.question_tokens, config.input_tokens, config.output_tokens) == (512, 6000, 1024)
    assert (config.ceiling_usd, config.working_usd, config.phase2_usd) == (
        Decimal("5"),
        Decimal("4"),
        Decimal("0.75"),
    )
    changed = config_type()(prompt_version="grounded-v2")
    assert changed.fingerprint() != config.fingerprint()
    assert config_type().model_validate_json(config.model_dump_json()) == config


@pytest.mark.parametrize(
    "update",
    [
        {"working_usd": "5"},
        {"phase2_usd": "1"},
        {"ceiling_usd": "6"},
        {"output_tokens": 1025},
        {"input_tokens": 6001},
        {"context_tokens": 3501},
        {"question_tokens": 513},
        {"chunk_tokens": 401},
        {"overlap_tokens": 400},
        {"scenario": "semantic"},
        {"generation_model": ""},
        {"phase2_usd": "NaN"},
        {"nebius_api_key": "should-not-enter-public-config"},
    ],
)
def test_invalid_or_over_budget_configuration_rejected(update):
    with pytest.raises(ValueError):
        config_type()(**update)


def test_two_provider_credentials_are_masked_and_redacted():
    import io

    from finsight.observability.logging import configure_logging

    settings = Settings(
        _env_file=None, nebius_api_key="synthetic-nebius", anthropic_api_key="synthetic-claude"
    )
    assert getattr(settings, "nebius_api_key", None) is not None
    assert getattr(settings, "anthropic_api_key", None) is not None
    assert "synthetic-nebius" not in settings.model_dump_json()
    assert "synthetic-claude" not in repr(settings)
    output = io.StringIO()
    configure_logging(settings, stream=output).error(
        "%s %s", "synthetic-nebius", "synthetic-claude"
    )
    assert "synthetic-nebius" not in output.getvalue()
    assert "synthetic-claude" not in output.getvalue()
    assert output.getvalue().count("[REDACTED]") == 2


def test_checked_in_baseline_config_can_load():
    path = Path(__file__).resolve().parents[2] / "configs/runtime/phase-2-baseline.json"
    assert path.is_file(), "Missing versioned baseline configuration"
    loaded = importlib.import_module("finsight.runtime.ports").load_baseline_config(path)
    assert (
        loaded.source_fingerprint
        == "7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3"
    )
    assert "api_key" not in json.dumps(loaded.model_dump(mode="json"))


def test_provider_constructors_are_keyless_and_local(tmp_path):
    assert importlib.util.find_spec("langchain_anthropic") is not None, (
        "Missing approved integration"
    )
    import chromadb
    from langchain_anthropic import ChatAnthropic
    from langchain_chroma import Chroma

    client = ChatAnthropic(
        model="claude-sonnet-5", api_key="synthetic-key", max_retries=0, timeout=20
    )
    assert client._client.max_retries == 0
    db = chromadb.PersistentClient(
        path=str(tmp_path / "index"), settings=chromadb.Settings(anonymized_telemetry=False)
    )
    store = Chroma(
        client=db,
        collection_name="synthetic",
        embedding_function=None,
        collection_configuration={"hnsw": {"space": "cosine"}},
    )
    assert store.get()["ids"] == []
