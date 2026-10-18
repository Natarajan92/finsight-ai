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
    from finsight.citations.validation import validate_draft
    from finsight.config import Settings
    from finsight.context.packing import pack_evidence
    from finsight.contracts import (
        Answer,
        BaselineConfig,
        RetrievalCandidate,
        SourceMetadata,
        UsageMetrics,
    )
    from finsight.contracts.generation import DraftAnswer
    from finsight.contracts.tracing import RunTrace
    from finsight.generation.prompts import build_prompt
    from finsight.indexing.catalog import create_catalog
    from finsight.ingestion.cache import extract_cached
    from finsight.ingestion.pages import CachedPageRepository
    from finsight.observability.tracing import JsonlTraceRecorder
    from finsight.runtime.ports import CallContext

    questions, corpus, split_dir, *_ = frozen_inputs
    config = BaselineConfig(
        source_fingerprint=corpus.source_fingerprint, chunk_tokens=40, overlap_tokens=5
    )
    settings = Settings(
        _env_file=None, trace_root=tmp_path / "traces", index_root=tmp_path / "indexes"
    )
    manifest = SimpleNamespace(fingerprint=lambda: "i" * 64)

    class Tokenizer:
        def count(self, text):
            return len(text)

        def offsets(self, text):
            return tuple((i, i + 1) for i in range(len(text)))

    pages = CachedPageRepository(corpus, questions.parent / "pdfs", tmp_path / "pages")
    for document in corpus.documents:
        extract_cached(pages.pdf_root, document, pages.extraction, pages.cache_root)
    tokenizer = Tokenizer()
    catalog = create_catalog(corpus, pages, config, tokenizer)
    chunk = next(c for c in catalog.chunks if "Revenue 1,000" in c.content)
    document = next(d for d in corpus.documents if d.document_id == chunk.document_id)
    candidate = RetrievalCandidate(
        chunk=chunk,
        source=SourceMetadata(**document.model_dump(include=set(SourceMetadata.model_fields))),
        rank=1,
        score=dict(kind="cosine_distance", direction="lower_is_better", value=0.1),
    )

    class Counter:
        def count_text(self, text, context):
            return 100

    monkeypatch.setattr(module, "local_assets", lambda *args: (corpus, pages, tokenizer))
    monkeypatch.setattr(
        module,
        "open_index",
        lambda *args, **kwargs: SimpleNamespace(
            manifest=manifest,
            catalog=catalog,
            store=SimpleNamespace(client=SimpleNamespace(close=lambda: None)),
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
            packet = prompt = draft = None
            retrieved = ()
            if "Predict" in request.question:
                answer = Answer(status="insufficient_evidence", limitations=("synthetic forecast",))
            else:
                retrieved = (candidate,)
                packet = pack_evidence(
                    retrieved,
                    pages,
                    request,
                    Counter(),
                    CallContext("synthetic", 2, 100, lambda: 0),
                    config,
                )
                prompt = build_prompt(request, packet)
                draft = DraftAnswer(
                    status="answered",
                    claims=[
                        dict(
                            text="Revenue was 1,000.",
                            references=[
                                dict(
                                    evidence_id=packet.slices[0].evidence_id, quote="Revenue 1,000"
                                )
                            ],
                        )
                    ],
                )
                answer = validate_draft(draft, packet, pages, UsageMetrics(), request=request)
            from finsight.contracts.base import fingerprint

            trace = RunTrace(
                run_id=self.last_trace_id,
                budget_id=config.budget_id,
                source_fingerprint=corpus.source_fingerprint,
                config_fingerprint=config.fingerprint(),
                request=request,
                request_fingerprint=fingerprint(request.model_dump(mode="json")),
                index_fingerprint=manifest.fingerprint(),
                filters=request.model_dump(mode="json", exclude={"question"}),
                rate_fingerprint="r" * 64,
                retrieved=retrieved,
                packet=packet,
                prompt=prompt,
                prompt_fingerprint=prompt.fingerprint if prompt else None,
                draft=draft,
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


@pytest.mark.parametrize(
    "changed",
    [
        "request_hash",
        "prompt",
        "chunk_id",
        "doc_name",
        "company",
        "fiscal_period",
        "span",
        "filters",
    ],
)
def test_campaign_replay_rejects_coherently_changed_trace(campaign_setup, changed):
    import json

    from finsight.citations.validation import validate_draft
    from finsight.contracts.base import fingerprint
    from finsight.contracts.documents import SourceSpan
    from finsight.generation.prompts import build_prompt
    from finsight.observability.tracing import JsonlTraceRecorder
    from finsight.runtime.errors import FinsightError

    module, settings, config, questions, directory, service = campaign_setup
    result = module.run_development_campaign(
        settings, config, questions, directory, allow_paid=True
    )
    trace = JsonlTraceRecorder(settings.trace_root).load(result["runs"][0]["trace_id"])
    if changed == "request_hash":
        trace = trace.model_copy(update={"request_fingerprint": "0" * 64})
    elif changed == "prompt":
        trace = trace.model_copy(
            update={"prompt": trace.prompt.model_copy(update={"user": "changed prompt"})}
        )
    elif changed == "filters":
        trace = trace.model_copy(update={"filters": {"company": "unrequested scope"}})
    else:
        evidence = trace.packet.slices[0]
        if changed == "chunk_id":
            evidence = evidence.model_copy(update={"chunk_id": "not-in-any-catalog"})
        elif changed == "span":
            _, pages, _ = module.local_assets(settings, config)
            page = pages.get(evidence.document_id, evidence.page_index)
            evidence = evidence.model_copy(
                update={
                    "source_spans": (
                        SourceSpan(
                            page_index=page.page_index, char_start=0, char_end=len(page.text)
                        ),
                    ),
                    "text": page.text,
                }
            )
        else:
            evidence = evidence.model_copy(
                update={
                    "source": evidence.source.model_copy(update={changed: "FORGED_2099_REPORT"})
                }
            )
        evidence = evidence.model_copy(
            update={
                "evidence_id": fingerprint(
                    {
                        "chunk_id": evidence.chunk_id,
                        "spans": [s.model_dump() for s in evidence.source_spans],
                    }
                )
            }
        )
        packet = trace.packet.model_copy(update={"slices": (evidence,)})
        reference = (
            trace.draft.claims[0]
            .references[0]
            .model_copy(update={"evidence_id": evidence.evidence_id})
        )
        claim = trace.draft.claims[0].model_copy(update={"references": (reference,)})
        draft = trace.draft.model_copy(update={"claims": (claim,)})
        _, pages, _ = module.local_assets(settings, config)
        answer = validate_draft(draft, packet, pages, trace.answer.usage, request=trace.request)
        prompt = build_prompt(trace.request, packet)
        trace = trace.model_copy(
            update={
                "packet": packet,
                "prompt": prompt,
                "prompt_fingerprint": prompt.fingerprint,
                "draft": draft,
                "answer": answer,
            }
        )
    (settings.trace_root / (trace.run_id + ".jsonl")).write_text(
        trace.model_dump_json(), encoding="utf-8"
    )
    result["runs"][0] = module._trace_summary(
        trace, result["runs"][0]["question_id"], result["runs"][0]["latency_ms"]
    )
    receipt_path = settings.trace_root / ("campaign-" + result["campaign_id"] + ".json")
    receipt = json.loads(receipt_path.read_text())
    receipt["runs"] = result["runs"]
    write_json_atomic(receipt_path, receipt)
    with pytest.raises(FinsightError, match="campaign_integrity"):
        module.run_development_campaign(settings, config, questions, directory, allow_paid=False)
    assert service.calls == 4
