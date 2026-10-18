"""Execute the shipped cells against real synthetic PDFs and blocked providers."""

import json
import shutil
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from finsight.contracts import BaselineConfig, ProviderUsage, QueryRequest
from finsight.contracts.generation import DraftAnswer
from finsight.contracts.tracing import ProviderAttempt
from finsight.observability.budget import BudgetLedger
from finsight.runtime.errors import FinsightError

NOTEBOOK = Path(__file__).resolve().parents[2] / "notebooks/01_single_document_rag.ipynb"


def notebook_cells():
    assert NOTEBOOK.is_file(), "Missing single-document architecture walkthrough notebook"
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


@pytest.fixture
def lab(index_setup, synthetic_rates, tmp_path, monkeypatch):
    cells = notebook_cells()
    _, corpus, pages, _, _, _, _, tokenizer = index_setup
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "project.md").write_text("Synthetic test checkout")
    (root / "pyproject.toml").write_text("[project]\nname='synthetic'")
    (root / "notebooks").mkdir()
    manifest = root / "data/manifests/financebench-selected.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(corpus.model_dump_json(), encoding="utf-8")
    shutil.copytree(pages.pdf_root, root / "source-data/pdfs")
    rates = root / "data/cache/budget/rates.json"
    rates.parent.mkdir(parents=True)
    rates.write_text(synthetic_rates.model_dump_json(), encoding="utf-8")
    ledger = BudgetLedger.initialize(
        rates.parent / "testing.sqlite3",
        "finsight-testing-2026-10-18",
        anchor_path=root / "results/testing-budget-identity.json",
    )
    (root / ".env").write_text("FINSIGHT_NEBIUS_API_KEY=synthetic-notebook-key\n")
    import finsight.chunking.tokenizer as tokenizers

    monkeypatch.setattr(
        tokenizers.TokenizerArtifact,
        "load",
        lambda path: SimpleNamespace(
            model="Qwen/Qwen3-Embedding-8B", revision=BaselineConfig().tokenizer_revision
        ),
    )
    monkeypatch.setattr(tokenizers, "LocalOffsetTokenizer", lambda artifact: tokenizer)
    # Other test modules may already have imported the factory's local binding.
    import finsight.runtime.factory as factory

    monkeypatch.setattr(factory, "LocalOffsetTokenizer", lambda artifact: tokenizer)
    requests = []
    fail = []

    def handle(request):
        requests.append(request)
        if fail:
            raise fail.pop(0)
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": body["model"],
                "data": [
                    {"index": i, "embedding": [1.0] + [0.0] * 4095}
                    for i in range(len(body["input"]))
                ],
                "usage": {"prompt_tokens": 5 * len(body["input"])},
            },
        )

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(handle))
    monkeypatch.chdir(root / "notebooks")
    namespace = {"__name__": "__notebook_test__"}
    before = manifest.read_bytes()
    for cell in cells:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), str(NOTEBOOK), "exec"), namespace)
    assert manifest.read_bytes() == before
    yield namespace, requests, fail, ledger
    namespace["close_resources"](run=True)


def test_notebook_is_unexecuted_and_every_code_cell_compiles():
    cells = notebook_cells()
    assert len(cells) >= 30
    for cell in cells:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is None and cell["outputs"] == []
            compile("".join(cell["source"]), str(NOTEBOOK), "exec")
    source = "\n".join("".join(c["source"]) for c in cells)
    assert "BudgetLedger.initialize" not in source
    assert "financebench_open_source.jsonl" not in source


def test_run_all_is_offline_and_scope_is_exactly_one_filing(lab):
    ns, requests, _, ledger = lab
    assert requests == [] and ledger.snapshot().accounted_usd == 0
    assert len(ns["scoped_corpus"].documents) == 1
    assert ns["document"].doc_name == "AMD_2022_10K"
    assert ns["config"].source_fingerprint != ns["parent_corpus"].source_fingerprint
    assert {c.document_id for c in ns["chunks"]} == {ns["document"].document_id}
    assert ns["draft"] is None and ns["answer"] is None


def test_complete_walkthrough_uses_same_index_packing_and_citation_functions(lab):
    ns, requests, _, ledger = lab
    ns["embed_next_batch"](run=True)
    manifest = ns["build_cached_index"]()
    assert manifest.complete and manifest.chunk_count == len(ns["chunks"])
    calls = len(requests)
    ns["build_cached_index"]()
    assert len(requests) == calls

    class Counter:
        def count_text(self, text, context):
            return max(1, len(text) // 4)

        def count_prompt(self, *args):
            return 1000

    class Generator:
        def generate(self, prompt, context):
            data = json.loads(prompt.user)
            evidence = next(s for s in data["sources"]["evidence"] if "Revenue 100" in s["text"])
            return DraftAnswer(
                status="answered",
                claims=[
                    dict(
                        text="Revenue was 100 USD millions in 2022.",
                        references=[dict(evidence_id=evidence["evidence_id"], quote="Revenue 100")],
                    )
                ],
            )

    ns["counter"], ns["generator"] = Counter(), Generator()
    ns["admit_question"](run=True)
    ns["embed_question"](run=True)
    candidates = ns["retrieve_evidence"]()
    assert all(c.chunk.document_id == ns["document"].document_id for c in candidates)
    ns["pack_context"](run=True)
    ns["make_prompt"]()
    ns["count_full_prompt"](run=True)
    ns["generate_draft"](run=True)
    result = ns["validate_answer"]()
    assert result.status == "answered" and result.citations
    assert all(c.document_id == ns["document"].document_id for c in result.citations)
    assert ledger.snapshot().reserved_usd == 0
    count = len(requests)
    ns["request"] = QueryRequest(
        question="Different question", document_ids=(ns["document"].document_id,)
    )
    with pytest.raises(FinsightError, match="notebook_stale_stage"):
        ns["retrieve_evidence"]()
    assert len(requests) == count


def test_index_stage_cannot_purchase_missing_embeddings(lab):
    ns, requests, _, ledger = lab
    assert ns["build_cached_index"]() is None
    assert not requests and ledger.snapshot().reserved_usd == 0


def test_timeout_stops_manual_batch_without_retry_or_releasing_money(lab):
    ns, requests, fail, ledger = lab
    fail.append(httpx.ReadTimeout("synthetic timeout"))
    with pytest.raises(FinsightError, match="provider_timeout"):
        ns["embed_next_batch"](run=True)
    assert len(requests) == 1
    assert ledger.snapshot().reserved_usd > 0
    assert ns["cache_progress"]()["cached_chunks"] == 0


def test_cell_pauses_do_not_reuse_an_expired_stage_deadline(lab):
    ns, *_ = lab
    clock = [100.0]
    ns["monotonic"] = lambda: clock[0]
    old = ns["stage_context"]("first")
    clock[0] += 120
    with pytest.raises(FinsightError, match="deadline_exceeded"):
        old.remaining()
    assert ns["stage_context"]("next").remaining() == 45


@pytest.mark.parametrize("missing", ["cost_usd", "output_tokens"])
def test_usage_preserves_each_unknown_field_and_counts_generation_separately(lab, missing):
    ns, *_ = lab
    usage = dict(input_tokens=11, output_tokens=3, cost_usd=Decimal("0.001"))
    usage[missing] = None
    ns["dispatcher"] = SimpleNamespace(
        attempts=(
            ProviderAttempt(
                request_id="embedding",
                run_id="synthetic",
                provider="nebius",
                model="synthetic",
                purpose="embedding",
                input_count=2,
                usage=ProviderUsage(
                    provider="nebius",
                    model="synthetic",
                    input_tokens=5,
                    output_tokens=0,
                    cost_usd=Decimal("0.0001"),
                    usage_known=True,
                ),
            ),
            ProviderAttempt(
                request_id="generation",
                run_id="synthetic",
                provider="anthropic",
                model="synthetic",
                purpose="generation",
                usage=ProviderUsage(
                    provider="anthropic",
                    model="synthetic",
                    usage_known=missing != "output_tokens",
                    **usage,
                ),
            ),
        )
    )
    result = ns["walkthrough_usage"]()
    assert getattr(result, missing) is None
    assert result.input_tokens == 16
    assert result.model_calls == 1 and result.embeddings == 2
