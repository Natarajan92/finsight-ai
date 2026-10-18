"""Small source-only builders; providers and tokenizers are deterministic fakes."""

import pytest

from finsight.contracts import DocumentManifest, Page


class CharacterTokenizer:
    def count(self, text):
        return len(text)

    def offsets(self, text):
        return tuple((i, i + 1) for i in range(len(text)))


@pytest.fixture
def char_tokenizer():
    return CharacterTokenizer()


@pytest.fixture
def page_factory(source):
    document = DocumentManifest(
        **source, document_id="synthetic-document", page_count=1, ingestion_version="synthetic-v1"
    )

    def make(text="Revenue 2022 | USD millions\nRevenue 1,000\nLoss (25)", **changes):
        data = dict(
            document_id=document.document_id,
            page_index=0,
            text=text,
            extraction_status="ok",
            parser_version="synthetic-v1",
        )
        data.update(changes)
        return document, Page(**data)

    return make


@pytest.fixture
def synthetic_rates():
    from datetime import UTC, datetime

    from finsight.contracts.budget import RateBook

    now = datetime.now(UTC)
    return RateBook(
        cards=[
            dict(
                provider="nebius",
                model="Qwen/Qwen3-Embedding-8B",
                input_per_million="1",
                output_per_million="0",
                source_url="https://nebius.com/token-factory/prices",
                verified_at=now,
            ),
            dict(
                provider="anthropic",
                model="claude-sonnet-5",
                input_per_million="1",
                output_per_million="5",
                source_url="https://platform.claude.com/docs/en/about-claude/pricing",
                verified_at=now,
            ),
        ]
    )


@pytest.fixture
def embedding_setup(tmp_path, char_tokenizer, synthetic_rates):
    import importlib
    import json

    import httpx
    from pydantic import SecretStr

    from finsight.contracts import BaselineConfig
    from finsight.observability.budget import BudgetLedger
    from finsight.observability.dispatch import GuardedDispatcher
    from finsight.runtime.ports import CallContext

    assert importlib.util.find_spec("finsight.indexing.nebius"), "Missing Nebius adapter"
    cache_module = importlib.import_module("finsight.indexing.embedding_cache")
    module = importlib.import_module("finsight.indexing.nebius")
    config = BaselineConfig(embedding_dimension=3)
    cache = cache_module.EmbeddingCache(tmp_path / "embeddings", config)
    ledger = BudgetLedger.initialize(tmp_path / "budget.sqlite3", config.budget_id)
    dispatcher = GuardedDispatcher(ledger, synthetic_rates)
    calls = []
    responses = []

    def handle(request):
        body = json.loads(request.content)
        calls.append((request, body))
        if responses:
            payload = responses.pop(0)
            if isinstance(payload, Exception):
                raise payload
            return httpx.Response(200, json=payload)
        return httpx.Response(
            200,
            json={
                "model": config.embedding_model,
                "data": [{"index": i, "embedding": [3, 4, 0]} for i in range(len(body["input"]))],
                "usage": {"prompt_tokens": sum(len(t) for t in body["input"])},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=False)
    backend = module.CachedNebiusEmbeddings(
        client=client,
        api_key=SecretStr("synthetic-key"),
        tokenizer=char_tokenizer,
        cache=cache,
        config=config,
        dispatcher=dispatcher,
    )
    bound = backend.for_run(CallContext("run", 2, 100, clock=lambda: 0))
    yield bound, cache, dispatcher, calls, responses
    client.close()


@pytest.fixture
def index_setup(tmp_path, pdf_factory, metadata_factory, char_tokenizer):
    import importlib

    from finsight.contracts import BaselineConfig
    from finsight.contracts.ingestion import ExtractionConfig
    from finsight.ingestion.cache import extract_cached
    from finsight.ingestion.manifest import build_manifest
    from finsight.runtime.ports import CallContext

    assert importlib.util.find_spec("finsight.indexing.builder"), "Missing index lifecycle"
    module = importlib.import_module("finsight.indexing.builder")
    repo_module = importlib.import_module("finsight.ingestion.pages")
    first = pdf_factory("AMD_2022_10K", ["Revenue USD millions 2022\nRevenue 100\n" * 20])
    pdf_factory("PepsiCo_2021_10K", ["Revenue USD millions 2021\nRevenue 200\n" * 20])
    metadata = metadata_factory(
        [
            dict(
                doc_name="AMD_2022_10K",
                company="AMD",
                doc_type="10K",
                doc_period=2022,
                doc_link=None,
            ),
            dict(
                doc_name="PepsiCo_2021_10K",
                company="PepsiCo",
                doc_type="10K",
                doc_period=2021,
                doc_link=None,
            ),
        ]
    )
    import json

    rows = [json.loads(line) for line in metadata.read_text().splitlines()]
    metadata.write_text("".join(json.dumps(dict(row, gics_sector=None)) + "\n" for row in rows))
    corpus = build_manifest(metadata, first.parent, ("AMD", "PepsiCo"), "phase1-v3")
    for doc in corpus.documents:
        extract_cached(first.parent, doc, ExtractionConfig(), tmp_path / "pages")
    repo = repo_module.CachedPageRepository(corpus, first.parent, tmp_path / "pages")
    config = BaselineConfig(source_fingerprint=corpus.source_fingerprint, embedding_dimension=3)

    class FakeEmbeddings:
        calls = 0
        queries = 0
        fail_after = None

        def for_run(self, context):
            return self

        def embed_documents(self, texts):
            self.calls += 1
            if self.fail_after is not None and self.calls > self.fail_after:
                raise RuntimeError("synthetic interruption")
            return [[1.0, 0.0, 0.0] for _ in texts]

        def embed_query(self, text):
            self.queries += 1
            return [1.0, 0.0, 0.0]

    embeddings = FakeEmbeddings()
    context = CallContext("index-run", 2, 1e20)
    root = tmp_path / "index"
    return module, corpus, repo, config, embeddings, root, context, char_tokenizer
