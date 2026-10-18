"""Claude admission uses its counting endpoint and bounded overhead padding."""

import importlib
from types import SimpleNamespace

import pytest

from finsight.contracts import BaselineConfig
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


def counting():
    assert importlib.util.find_spec("finsight.generation.counting"), "Missing Claude counting"
    return importlib.import_module("finsight.generation.counting")


def test_full_prompt_padding_and_rejection():
    module = counting()
    assert module.admit_input_tokens(5000, BaselineConfig()) == 5512
    with pytest.raises(FinsightError, match="input_token_limit"):
        module.admit_input_tokens(5500, BaselineConfig())


def test_model_count_cache_and_serialized_schema_are_counted():
    module = counting()
    calls = []

    class Client:
        max_retries = 0

        def __init__(self):
            self.messages = self

        def with_options(self, **options):
            assert options == {"max_retries": 0, "timeout": 20}
            return self

        def count_tokens(self, **body):
            calls.append(body)
            return SimpleNamespace(input_tokens=73)

    counter = module.ClaudeTokenCounter(Client(), "claude-sonnet-5")
    context = CallContext("run", 2, 100, clock=lambda: 0)
    schema = {"type": "object", "properties": {"claim": {"type": "string"}}}
    assert counter.count_prompt("system", "question", schema, context) == 73
    assert counter.count_prompt("system", "question", schema, context) == 73
    assert len(calls) == 1
    assert calls[0]["model"] == "claude-sonnet-5"
    assert '"claim"' in calls[0]["messages"][0]["content"]
    assert len(counter.attempts) == 1
    assert counter.attempts[0].purpose == "free_token_count"


def test_counter_failure_is_explicit_and_never_falls_back():
    module = counting()

    class Broken:
        def with_options(self, **kwargs):
            raise TimeoutError()

    counter = module.ClaudeTokenCounter(Broken(), "claude-sonnet-5")
    with pytest.raises(FinsightError, match="token_count_unavailable"):
        counter.count_text("question", CallContext("run", 2, 100, clock=lambda: 0))
    assert counter.attempts[0].error_code == "token_count_unavailable"


def test_question_limit_and_deadline():
    module = counting()

    class Counter:
        def count_text(self, text, context):
            return len(text)

    context = CallContext("run", 2, 100, clock=lambda: 0)
    with pytest.raises(FinsightError, match="question_token_limit"):
        module.validate_question("x" * 513, Counter(), context, BaselineConfig())
    with pytest.raises(FinsightError, match="deadline_exceeded"):
        module.validate_question(
            "small", Counter(), CallContext("run", 2, 0, clock=lambda: 1), BaselineConfig()
        )


def test_counting_is_bounded_by_elapsed_application_deadline():
    from threading import Event
    from time import monotonic

    release, finished = Event(), Event()

    class Slow:
        def with_options(self, **options):
            self.messages = self
            return self

        def count_tokens(self, **body):
            try:
                release.wait(2)
                return SimpleNamespace(input_tokens=12)
            finally:
                finished.set()

    counter = counting().ClaudeTokenCounter(Slow(), "claude-sonnet-5")
    started = monotonic()
    try:
        with pytest.raises(FinsightError):
            counter.count_text("question", CallContext("run", 2, monotonic() + 0.05))
        assert monotonic() - started < 0.5
        assert len(counter.attempts) == 1
    finally:
        release.set()
        assert finished.wait(1)
    assert counter.records == []
    assert counter._counts == {}
