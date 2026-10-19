"""AMD answers exercise real PDFs, Chroma, service validation and Streamlit."""

import importlib.util
import json
import socket
from dataclasses import replace

import pytest

from finsight.application import BaselineApplicationService
from finsight.config import Settings
from finsight.contracts import BaselineConfig, QueryRequest
from finsight.contracts.base import fingerprint
from finsight.contracts.generation import DraftAnswer
from finsight.contracts.ingestion import CorpusManifest
from finsight.observability.tracing import JsonlTraceRecorder
from finsight.runtime.errors import FinsightError
from finsight.runtime.experiment_factory import ExperimentLab

SOCKET_CONNECT = socket.socket.connect


@pytest.fixture
def streamlit_socketpair(monkeypatch):
    """Permit only asyncio's private socketpair construction on Windows.

    Windows implements socketpair using a loopback connect. Keep application
    socket connections blocked outside this standard-library helper.
    """
    original_pair = socket.socketpair

    def private_pair(*args, **kwargs):
        with monkeypatch.context() as local:
            local.setattr(socket.socket, "connect", SOCKET_CONNECT)
            return original_pair(*args, **kwargs)

    monkeypatch.setattr(socket, "socketpair", private_pair)


@pytest.fixture
def amd_lab(index_setup, embedding_setup, tmp_path, monkeypatch):
    _, parent, pages, _, _, _, _, tokenizer = index_setup
    doc = next(d for d in parent.documents if d.company == "AMD")
    corpus = CorpusManifest(
        documents=(doc,),
        metadata_sha256=parent.metadata_sha256,
        source_fingerprint=fingerprint([[doc.doc_name, doc.sha256]]),
    )
    config = BaselineConfig(source_fingerprint=corpus.source_fingerprint, embedding_dimension=3)
    backend, cache, dispatcher, calls, _ = embedding_setup
    backend = replace(backend, config=config)
    rates = tmp_path / "rates.json"
    rates.write_text(dispatcher.rates.model_dump_json())
    settings = Settings(
        _env_file=None,
        source_pdf_dir=pages.pdf_root,
        page_cache_root=pages.cache_root,
        index_root=tmp_path / "amd-index",
        trace_root=tmp_path / "traces",
        embedding_cache_root=cache.root,
        ledger_path=dispatcher.ledger.path,
        budget_anchor_path=dispatcher.ledger.anchor,
        rates_path=rates,
    )
    lab = ExperimentLab(
        settings, corpus, pages, tokenizer, baseline=config, backend=backend, dispatcher=dispatcher
    )
    chunks = lab.catalog("A").chunks
    for start in range(0, len(chunks), 4):
        backend.for_run(lab.context("prepare")).embed_documents(
            [c.content for c in chunks[start : start + 4]]
        )
    lab.build_index("A")

    class Counter:
        def count_text(self, text, context):
            return max(1, len(text) // 4)

        def count_prompt(self, *args):
            return 1000

    class Generator:
        calls = 0
        failure = False
        abstain = False

        def generate(self, prompt, context):
            self.calls += 1
            if self.failure:
                raise RuntimeError("PRIVATE_PROVIDER_KEY")
            if self.abstain:
                return DraftAnswer(status="insufficient_evidence", limitations=("Not in filing.",))
            item = json.loads(prompt.user)["sources"]["evidence"][0]
            return DraftAnswer(
                status="answered",
                claims=[
                    dict(
                        text="Revenue was 100 USD millions in 2022.",
                        references=[dict(evidence_id=item["evidence_id"], quote="Revenue 100")],
                    )
                ],
            )

    generator = Generator()
    retriever = lab.open("A")
    retriever.embeddings = backend
    service = BaselineApplicationService(
        config,
        retriever,
        Counter(),
        generator,
        pages,
        JsonlTraceRecorder(lab.trace_root / "answers"),
        phase=3,
        run_fingerprint=lab.config("A").fingerprint(),
    )
    monkeypatch.setattr(lab, "application", lambda *args, **kwargs: service)
    yield lab, generator, calls, service
    lab.close()


def pilot():
    assert importlib.util.find_spec("finsight.runtime.experiment_pilot"), (
        "Missing durable AMD answers"
    )
    from finsight.runtime.experiment_pilot import ask_pilot

    return ask_pilot


def test_amd_live_is_explicit_and_replay_is_free(amd_lab):
    lab, generator, calls, service = amd_lab
    ask = pilot()
    request = QueryRequest(question="What was revenue in 2022?")
    count = len(calls)
    with pytest.raises(FinsightError, match="paid_not_authorized"):
        ask(lab, request, "A")
    assert generator.calls == 0 and len(calls) == count
    result = ask(lab, request, "A", allow_paid=True)
    assert result["answer"]["status"] == "answered" and result["replay"] is False
    assert result["answer"]["citations"][0]["page_index"] == 0
    assert service.last_trace.request.company == "AMD"
    assert service.last_trace.request.document_ids == (lab.corpus.documents[0].document_id,)
    replay = ask(lab, request, "A")
    assert replay["answer"] == result["answer"] and replay["replay"] is True
    assert generator.calls == 1 and len(calls) == count + 1


@pytest.mark.parametrize(
    "scope", [dict(company="PepsiCo"), dict(period="2021"), dict(document_ids=("other",))]
)
def test_wrong_scope_never_purchases(amd_lab, scope):
    lab, generator, calls, _ = amd_lab
    count = len(calls)
    with pytest.raises(FinsightError, match="experiment_pilot_scope"):
        pilot()(lab, QueryRequest(question="Revenue?", **scope), "A", allow_paid=True)
    assert generator.calls == 0 and len(calls) == count


def test_error_receipt_does_not_repurchase_and_hides_provider_exception(amd_lab):
    lab, generator, _, _ = amd_lab
    generator.failure = True
    request = QueryRequest(question="Revenue in 2022?")
    result = pilot()(lab, request, "A", allow_paid=True)
    assert result["answer"]["status"] == "error"
    assert "PRIVATE_PROVIDER_KEY" not in json.dumps(result)
    again = pilot()(lab, request, "A", allow_paid=True)
    assert again["replay"] and generator.calls == 1


def test_started_or_corrupt_receipt_cannot_dispatch(amd_lab):
    lab, generator, _, _ = amd_lab
    ask = pilot()
    request = QueryRequest(question="Revenue in 2022?")
    ask(lab, request, "A", allow_paid=True)
    path = next((lab.trace_root / "pilot").rglob("answer.json"))
    raw = json.loads(path.read_text())
    raw["complete"] = False
    path.write_text(json.dumps(raw))
    with pytest.raises(FinsightError, match="experiment_interrupted"):
        ask(lab, request, "A", allow_paid=True)
    raw["complete"] = True
    raw["result"]["answer"]["answer_text"] = "FORGED"
    path.write_text(json.dumps(raw))
    with pytest.raises(FinsightError, match="experiment_replay_integrity"):
        ask(lab, request, "A", allow_paid=True)
    assert generator.calls == 1


def test_cached_citation_must_still_match_source(amd_lab, monkeypatch):
    lab, generator, _, _ = amd_lab
    request = QueryRequest(question="Revenue in 2022?")
    ask = pilot()
    ask(lab, request, "A", allow_paid=True)
    original = lab.pages.get
    monkeypatch.setattr(
        lab.pages,
        "get",
        lambda doc, page: original(doc, page).model_copy(update={"text": "changed"}),
    )
    with pytest.raises(FinsightError, match="experiment_replay_integrity"):
        ask(lab, request, "A", allow_paid=True)
    assert generator.calls == 1


def workspace(lab):
    assert importlib.util.find_spec("finsight.ui.workspace"), "Missing AMD workspace"
    from finsight.ui.workspace import AmdWorkspace

    return AmdWorkspace(lab)


def test_workspace_real_source_and_one_based_page_bounds(amd_lab):
    lab, generator, calls, _ = amd_lab
    count = len(calls)
    ws = workspace(lab)
    assert ws.document.doc_name == "AMD_2022_10K" and ws.chunk_count > 0
    assert "Revenue 100" in ws.page(1).text
    for number in (0, 2, True):
        with pytest.raises(FinsightError, match="page_unavailable"):
            ws.page(number)
    assert generator.calls == 0 and len(calls) == count


def render_test_app(ws):
    from finsight.ui.app import render

    render(ws)


def app_test(ws):
    assert importlib.util.find_spec("finsight.ui.app"), "Missing Streamlit application"
    from streamlit.testing.v1 import AppTest

    return AppTest.from_function(render_test_app, args=(ws,), default_timeout=15).run()


def test_streamlit_startup_submit_and_rerun_keep_answer_without_duplicate_calls(
    amd_lab, streamlit_socketpair
):
    lab, generator, calls, _ = amd_lab
    count = len(calls)
    app = app_test(workspace(lab))
    assert not app.exception
    assert generator.calls == 0 and len(calls) == count
    app.text_area(key="question").input("What was revenue in 2022?")
    app.button(key="ask").click().run()
    assert generator.calls == 0
    assert app.info and "live" in " ".join(x.value.lower() for x in app.info)
    app.toggle(key="live").set_value(True).run()
    app.button(key="ask").click().run()
    assert not app.exception and generator.calls == 1
    assert any("100 USD millions" in x.value for x in app.text)
    assert any("PDF page 1" in x.label for x in app.expander)
    app.run()
    app.button(key="ask").click().run()
    assert not app.exception and generator.calls == 1
    assert any("Saved answer" in x.value for x in app.caption)


def test_streamlit_abstention_and_safe_setup_failure(amd_lab, streamlit_socketpair):
    lab, generator, _, _ = amd_lab
    generator.abstain = True
    app = app_test(workspace(lab))
    app.toggle(key="live").set_value(True).run()
    app.text_area(key="question").input("What is the missing figure?")
    app.button(key="ask").click().run()
    assert not app.exception and any("Not in filing." in x.value for x in app.text)

    ws = workspace(lab)
    ws.ask = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("PRIVATE_PROVIDER_KEY"))
    app = app_test(ws)
    app.toggle(key="live").set_value(True).run()
    app.text_area(key="question").input("Revenue?")
    app.button(key="ask").click().run()
    assert not app.exception and app.error
    assert "PRIVATE_PROVIDER_KEY" not in " ".join(x.value for x in app.error)


def test_streamlit_rerun_revalidates_receipt_before_showing_saved_answer(
    amd_lab, streamlit_socketpair
):
    lab, generator, _, _ = amd_lab
    app = app_test(workspace(lab))
    app.toggle(key="live").set_value(True).run()
    app.text_area(key="question").input("Revenue in 2022?")
    app.button(key="ask").click().run()
    assert generator.calls == 1
    path = next((lab.trace_root / "pilot").rglob("answer.json"))
    path.write_text("{}")
    app.run()
    assert not app.exception and app.error
    assert not any("100 USD millions" in item.value for item in app.text)
    assert generator.calls == 1


def render_literal_answer(result):
    from finsight.ui.app import _answer

    _answer(result)


def test_currency_and_untrusted_markdown_are_rendered_as_literal_text(
    amd_lab, streamlit_socketpair
):
    from streamlit.testing.v1 import AppTest

    lab, _, _, _ = amd_lab
    result = pilot()(lab, QueryRequest(question="Revenue in 2022?"), "A", allow_paid=True)
    prose = "$100 million (approximately $0.1 billion). [1]\n![x](https://example.test/track)"
    limitation = "Unit comparison: $100 versus $90."
    result["answer"]["answer_text"] = prose
    result["answer"]["limitations"] = [limitation]
    app = AppTest.from_function(render_literal_answer, args=(result,), default_timeout=15).run()
    assert not app.exception
    assert any(item.value == prose for item in app.text)
    assert any(item.value == limitation for item in app.text)
