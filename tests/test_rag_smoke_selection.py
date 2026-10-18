"""Development-only selection never turns benchmark labels into runtime filters."""

import importlib

import pytest

from finsight.evaluation.benchmark import load_benchmark
from finsight.evaluation.splits import SplitPolicy, freeze_splits, write_splits
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file


@pytest.fixture
def frozen_inputs(benchmark_fixture, tmp_path):
    questions, corpus, _ = benchmark_fixture
    cases = load_benchmark(questions, corpus)
    policy = SplitPolicy(dataset_sha256=sha256_file(questions))
    dev, hold = freeze_splits(cases, policy, sha256_file(questions), corpus.source_fingerprint)
    directory = tmp_path / "split"
    write_splits(directory, dev, hold)
    write_json_atomic(directory / "split-policy.json", policy.model_dump(mode="json"))
    return questions, corpus, directory, cases, dev, hold


def selector():
    assert importlib.util.find_spec("finsight.evaluation.smoke"), (
        "Missing development smoke selector"
    )
    return importlib.import_module("finsight.evaluation.smoke").select_development_cases


def test_three_distinct_companies_from_frozen_development_only(frozen_inputs):
    questions, corpus, directory, cases, dev, hold = frozen_inputs
    selected = selector()(questions, corpus, directory)
    by_id = {c.financebench_id: c for c in cases}
    assert len(selected) == 3
    assert len({by_id[c.question_id].company for c in selected}) == 3
    assert all(
        c.question_id in dev.question_ids and c.question_id not in hold.question_ids
        for c in selected
    )
    assert selected == selector()(questions, corpus, directory)
    for case in selected:
        assert case.request.question == by_id[case.question_id].question
        assert case.request.company is None and case.request.period is None
        assert case.request.document_ids is None
        assert "answer" not in type(case.request).model_fields
        assert "evidence" not in type(case.request).model_fields


def test_changed_split_or_dataset_is_rejected(frozen_inputs):
    questions, corpus, directory, *_ = frozen_inputs
    selector()(questions, corpus, directory)
    questions.write_text(questions.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        selector()(questions, corpus, directory)


def test_invalid_count_rejected(frozen_inputs):
    questions, corpus, directory, *_ = frozen_inputs
    with pytest.raises(ValueError):
        selector()(questions, corpus, directory, count=0)


@pytest.fixture
def campaign_setup(frozen_inputs, tmp_path, monkeypatch):
    selector()
    from types import SimpleNamespace

    import finsight.evaluation.smoke as module
    from finsight.config import Settings
    from finsight.contracts import Answer, BaselineConfig
    from finsight.contracts.tracing import RunTrace
    from finsight.observability.tracing import JsonlTraceRecorder

    questions, corpus, split_dir, *_ = frozen_inputs
    config = BaselineConfig(source_fingerprint=corpus.source_fingerprint)
    settings = Settings(
        _env_file=None, trace_root=tmp_path / "traces", index_root=tmp_path / "indexes"
    )
    manifest = SimpleNamespace(fingerprint=lambda: "i" * 64)
    monkeypatch.setattr(module, "local_assets", lambda *args: (corpus, None, None))
    monkeypatch.setattr(
        module,
        "open_index",
        lambda *args, **kwargs: SimpleNamespace(
            manifest=manifest, store=SimpleNamespace(client=SimpleNamespace(close=lambda: None))
        ),
    )
    monkeypatch.setattr(module, "preflight", lambda *args: {"status": "ready"})
    snapshot = SimpleNamespace(
        model_dump=lambda **kwargs: {"reserved_usd": "0", "accounted_usd": "0"}
    )
    monkeypatch.setattr(
        module,
        "spending_setup",
        lambda *args: (
            SimpleNamespace(fingerprint=lambda: "r" * 64),
            SimpleNamespace(snapshot=lambda: snapshot),
        ),
    )
    sink = JsonlTraceRecorder(settings.trace_root)

    class Service:
        calls = 0
        fail_at = None

        def answer(self, request):
            self.calls += 1
            if self.calls == self.fail_at:
                raise RuntimeError("synthetic process interruption")
            self.last_trace_id = "trace" + str(self.calls)
            answer = Answer(
                status="insufficient_evidence", limitations=("missing synthetic facts",)
            )
            from finsight.contracts.base import fingerprint

            trace = RunTrace(
                run_id=self.last_trace_id,
                budget_id=config.budget_id,
                source_fingerprint=corpus.source_fingerprint,
                config_fingerprint=config.fingerprint(),
                request=request,
                request_fingerprint=fingerprint(request.model_dump(mode="json")),
                index_fingerprint=manifest.fingerprint(),
                answer=answer,
            )
            sink.record(trace)
            return answer

        def close(self):
            pass

    service = Service()
    monkeypatch.setattr(module, "create_application", lambda *args, **kwargs: service)
    return module, settings, config, questions, split_dir, service


def test_completed_campaign_replays_without_new_service_calls(campaign_setup):
    module, settings, config, questions, directory, service = campaign_setup
    result = module.run_development_campaign(
        settings, config, questions, directory, allow_paid=True
    )
    assert len(result["runs"]) == 4 and service.calls == 4 and not result["replay"]
    replay = module.run_development_campaign(
        settings, config, questions, directory, allow_paid=False
    )
    assert replay["replay"] and service.calls == 4


def test_interrupted_campaign_never_automatically_buys_again(campaign_setup):
    from finsight.runtime.errors import FinsightError

    module, settings, config, questions, directory, service = campaign_setup
    service.fail_at = 2
    with pytest.raises(RuntimeError):
        module.run_development_campaign(settings, config, questions, directory, allow_paid=True)
    with pytest.raises(FinsightError, match="campaign_interrupted"):
        module.run_development_campaign(settings, config, questions, directory, allow_paid=True)
    assert service.calls == 2
