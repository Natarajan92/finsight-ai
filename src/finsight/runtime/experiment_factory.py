"""Explicit experiment facade shared by CLI and notebooks; constructors are offline."""

from decimal import Decimal
from time import monotonic
from uuid import uuid4

import httpx

from finsight.application import BaselineApplicationService
from finsight.chunking.semantic import (
    load_preparation,
    prepare_semantics,
    semantic_chunk_pages,
    semantic_units,
)
from finsight.chunking.semantic_cache import cache_progress, embed_next_units
from finsight.chunking.tokenizer import LocalOffsetTokenizer, TokenizerArtifact
from finsight.contracts import BaselineConfig
from finsight.contracts.ingestion import CorpusManifest
from finsight.contracts.retrieval_experiments import RetrievalExperimentConfig
from finsight.generation.claude import ClaudeGenerator, create_chat
from finsight.generation.counting import ClaudeTokenCounter
from finsight.indexing.builder import build_index, open_index
from finsight.indexing.catalog import create_catalog
from finsight.indexing.embedding_cache import EmbeddingCache
from finsight.indexing.nebius import CachedNebiusEmbeddings
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import source_fingerprint
from finsight.ingestion.pages import CachedPageRepository
from finsight.observability.dispatch import GuardedDispatcher
from finsight.observability.tracing import JsonlTraceRecorder
from finsight.retrieval.experiments import run_arms
from finsight.retrieval.reranker_artifacts import OnnxCrossEncoder
from finsight.retrieval.reranking import LocalReranker
from finsight.runtime.errors import FinsightError
from finsight.runtime.factory import spending_setup
from finsight.runtime.ports import CallContext

from .experiment_storage import CachedEmbeddingsOnly, retrieve_pool


class ExperimentRetriever:
    def __init__(self, lab, arm, allow_paid):
        self.lab, self.arm, self.allow_paid = lab, arm, allow_paid
        cfg = lab.config(arm)
        self.chunk_strategy, self.rerank = cfg.chunk_strategy, cfg.rerank
        base = lab.open(arm)
        self.manifest, self.corpus = base.manifest, base.corpus
        self.embeddings = (
            lab._backend if lab._backend is not None else CachedEmbeddingsOnly(lab.cache)
        )

    def retrieve(self, request, context):
        cfg = self.lab.config(self.arm)
        plain = type(request)(**{**request.model_dump(), "rerank": False})
        pool = self.lab.pool(cfg.chunk_strategy, plain, context, allow_paid=self.allow_paid)
        if cfg.rerank:
            return self.lab.reranker.rerank(request.question, pool.candidates, context).candidates
        return pool.candidates


class ExperimentLab:
    def __init__(
        self,
        settings,
        corpus,
        pages,
        tokenizer,
        *,
        baseline=None,
        phase3_usd=Decimal("0.75"),
        backend=None,
        dispatcher=None,
        reranker=None,
    ):
        self.settings, self.corpus, self.pages, self.tokenizer = settings, corpus, pages, tokenizer
        self.baseline = baseline or BaselineConfig(source_fingerprint=corpus.source_fingerprint)
        if self.baseline.source_fingerprint != corpus.source_fingerprint:
            raise FinsightError("source_integrity")
        self.phase3_usd = RetrievalExperimentConfig(phase3_usd=phase3_usd).phase3_usd
        self.cache = EmbeddingCache(settings.embedding_cache_root, self.baseline)
        self.cache_root = settings.embedding_cache_root.parent
        self.trace_root = settings.trace_root / "phase3" / corpus.source_fingerprint[:12]
        self.model_root = self.cache_root / "models" / "ms-marco-minilm-l6-v2"
        self._backend, self.dispatcher, self._reranker = backend, dispatcher, reranker
        self._client = self._chat = self._counter = self._generator = None
        self._retrievers = {}
        self._units = None
        self.last_traces = ()

    def config(self, arm):
        return RetrievalExperimentConfig(
            arm=arm, baseline=self.baseline, phase3_usd=self.phase3_usd
        )

    def context(self, purpose, seconds=None):
        return CallContext(
            uuid4().hex, 3, monotonic() + (self.baseline.deadline_s if seconds is None else seconds)
        )

    def documents(self):
        for document in sorted(self.corpus.documents, key=lambda d: d.document_id):
            yield (
                document,
                tuple(self.pages.get(document.document_id, i) for i in range(document.page_count)),
            )

    def units(self):
        if self._units is None:
            config = self.config("B").index_config()
            self._units = tuple(
                u for d, p in self.documents() for u in semantic_units(d, p, config, self.tokenizer)
            )
        return self._units

    def semantic_progress(self):
        progress = cache_progress(self.units(), self.cache)
        return {k: v for k, v in progress.items() if k != "missing_texts"}

    def semantic_root(self, document):
        return self.cache_root / "semantic" / document.document_id[-16:]

    def prepare_semantic(self):
        config = self.config("B").index_config()
        return tuple(
            prepare_semantics(d, p, config, self.tokenizer, self.cache, self.semantic_root(d))
            for d, p in self.documents()
        )

    def chunker(self, document, pages, config, tokenizer):
        prep = load_preparation(
            document, pages, config, tokenizer, self.cache, self.semantic_root(document)
        )
        return semantic_chunk_pages(document, pages, config, tokenizer, prep)

    def catalog(self, arm):
        config = self.config(arm)
        return create_catalog(
            self.corpus,
            self.pages,
            config.index_config(),
            self.tokenizer,
            chunker=self.chunker if config.chunk_strategy == "semantic" else None,
        )

    def _missing_chunks(self, arm):
        missing = {}
        for chunk in self.catalog(arm).chunks:
            key = self.cache.key(chunk.content, "document")
            if self.cache.get(key) is None:
                missing.setdefault(key, chunk.content)
        return tuple(missing.values())

    def chunk_progress(self, arm):
        catalog = self.catalog(arm)
        return dict(
            total_chunks=len(catalog.chunks), missing_unique_inputs=len(self._missing_chunks(arm))
        )

    def index_path(self, arm):
        config = self.config(arm)
        index = config.index_config()
        if config.chunk_strategy == "fixed":
            candidates = [self.settings.index_root / index.fingerprint()]
            if len(self.corpus.documents) == 1:
                candidates.append(
                    self.settings.index_root
                    / "notebook"
                    / self.corpus.documents[0].document_id[-16:]
                    / index.fingerprint()[:16]
                )
            for candidate in candidates:
                if (candidate / "manifest.json").is_file():
                    return candidate
        return (
            self.settings.index_root
            / "phase3"
            / self.corpus.source_fingerprint[:12]
            / index.fingerprint()[:16]
        )

    def _spending(self):
        rates, ledger = spending_setup(self.settings, self.baseline)
        return rates, ledger

    def preflight(self, stage="semantic", *, query_count=4):
        if (
            stage not in {"semantic", "index", "comparison"}
            or type(query_count) is not int
            or not 0 <= query_count <= 36
        ):
            raise FinsightError("experiment_configuration")
        rates, ledger = self._spending()
        snapshot = ledger.snapshot()
        allowed = min(
            snapshot.available_usd,
            ledger.phase_available(3, limit_usd=self.phase3_usd),
            max(Decimal(0), self.baseline.working_usd - (Decimal(4) - snapshot.available_usd)),
        )
        if stage == "semantic":
            inputs = cache_progress(self.units(), self.cache)["missing_texts"]
        elif stage == "index":
            inputs = tuple(dict.fromkeys(self._missing_chunks("A") + self._missing_chunks("B")))
        else:
            for arm in "AB":
                self.open(arm)
            inputs = ()
        tokens = sum(self.tokenizer.count(t) + 64 for t in inputs)
        if stage == "comparison":
            tokens = query_count * (32768 + 64)
        card = rates.card("nebius", self.baseline.embedding_model)
        requests = (len(inputs) + 3) // 4 if stage != "comparison" else query_count
        maximum = card.maximum(tokens, 0) * 2 + Decimal("0.000001") * requests * 2
        return dict(
            status="ready" if maximum <= allowed else "budget_conflict",
            stage=stage,
            maximum_usd=str(maximum),
            available_usd=str(allowed),
            phase=3,
            phase_cap_usd=str(self.phase3_usd),
            uncached_inputs=len(inputs),
            reservation_tokens=tokens,
            budget=snapshot.model_dump(mode="json"),
            provider_network_calls=0,
            rate_fingerprint=rates.fingerprint(),
        )

    def backend(self):
        rates, ledger = self._spending()
        if (
            self.dispatcher is not None
            and self.dispatcher.rates.fingerprint() != rates.fingerprint()
        ):
            raise FinsightError("experiment_configuration_changed")
        if self._backend is None:
            if (
                not self.settings.nebius_api_key
                or self.baseline.embedding_model != "Qwen/Qwen3-Embedding-8B"
                or self.baseline.embedding_dimension != 4096
            ):
                raise FinsightError("credentials_missing")
            self.dispatcher = GuardedDispatcher(
                ledger, rates, config=self.baseline, phase3_usd=self.phase3_usd
            )
            self._client = httpx.Client(
                transport=httpx.HTTPTransport(retries=0),
                timeout=self.baseline.attempt_timeout_s,
                follow_redirects=False,
            )
            self._backend = CachedNebiusEmbeddings(
                self._client,
                self.settings.nebius_api_key,
                self.tokenizer,
                self.cache,
                self.baseline,
                self.dispatcher,
            )
        return self._backend

    def _batches(self, batches, batch_size):
        if (
            type(batches) is not int
            or not 1 <= batches <= 10000
            or type(batch_size) is not int
            or not 1 <= batch_size <= 4
        ):
            raise FinsightError("experiment_configuration")

    def embed_semantic(self, *, allow_paid=False, batches=1, batch_size=4):
        self._batches(batches, batch_size)
        if not self.semantic_progress()["missing_unique_inputs"]:
            return self.semantic_progress()
        if not allow_paid:
            raise FinsightError("paid_not_authorized")
        if self.preflight("semantic")["status"] != "ready":
            raise FinsightError("budget_exceeded")
        for _ in range(batches):
            progress = embed_next_units(
                self.units(),
                self.cache,
                self.backend(),
                self.context("semantic"),
                batch_size=batch_size,
            )
            if not progress["missing_unique_inputs"]:
                break
        return self.semantic_progress()

    def embed_chunks(self, arm="A", *, allow_paid=False, batches=1, batch_size=4):
        self._batches(batches, batch_size)
        if self._missing_chunks(arm) and not allow_paid:
            raise FinsightError("paid_not_authorized")
        if self._missing_chunks(arm) and self.preflight("index")["status"] != "ready":
            raise FinsightError("budget_exceeded")
        for _ in range(batches):
            missing = self._missing_chunks(arm)
            if not missing:
                break
            self.backend().for_run(self.context("chunks")).embed_documents(
                list(missing[:batch_size])
            )
        return self.chunk_progress(arm)

    def build_index(self, arm="A"):
        if self._missing_chunks(arm):
            raise FinsightError("experiment_embeddings_missing")
        strategy = self.config(arm).chunk_strategy
        if strategy in self._retrievers:
            self._retrievers.pop(strategy).store.client.close()
        return build_index(
            self.corpus,
            self.pages,
            self.config(arm).index_config(),
            CachedEmbeddingsOnly(self.cache),
            self.index_path(arm),
            self.context("index", self.settings.index_job_timeout_s),
            tokenizer=self.tokenizer,
            chunker=self.chunker if strategy == "semantic" else None,
        )

    def open(self, arm):
        strategy = self.config(arm).chunk_strategy
        if strategy not in self._retrievers:
            self._retrievers[strategy] = open_index(
                self.index_path(arm),
                self.config(arm).index_config(),
                self.corpus,
                pages=self.pages,
                embeddings=CachedEmbeddingsOnly(self.cache),
                tokenizer=self.tokenizer,
                chunker=self.chunker if strategy == "semantic" else None,
            )
        return self._retrievers[strategy]

    @property
    def reranker(self):
        if self._reranker is None:
            config = self.config("C").reranker
            self._reranker = LocalReranker(
                OnnxCrossEncoder(self.model_root, config), config, self.cache_root / "reranking"
            )
        return self._reranker

    def pool(self, strategy, request, context, *, allow_paid=False, attempt_id="primary"):
        if self.tokenizer.count(request.question) > self.baseline.question_tokens:
            raise FinsightError("question_token_limit")
        arm = "A" if strategy == "fixed" else "B"
        return retrieve_pool(
            self.trace_root,
            self.open(arm),
            request,
            context,
            self.cache,
            self.backend,
            allow_paid=allow_paid,
            attempt_id=attempt_id,
        )

    def run_arms(self, request, *, allow_paid=False, arms="ABCD", attempt_id="primary"):
        configs = tuple(self.config(a) for a in arms)
        reranker = self.reranker if any(c.rerank for c in configs) else None
        traces = run_arms(
            request,
            configs,
            lambda strategy, req, ctx: self.pool(
                strategy, req, ctx, allow_paid=allow_paid, attempt_id=attempt_id
            ),
            reranker,
            self.context,
        )
        for trace in traces:
            write_json_atomic(
                self.trace_root / "arms" / (trace.run_id + ".json"), trace.model_dump(mode="json")
            )
        self.last_traces = traces
        return traces

    def application(self, arm, *, allow_paid=False):
        if not allow_paid:
            raise FinsightError("paid_not_authorized")
        self.backend()
        if self._generator is None:
            if not self.settings.anthropic_api_key:
                raise FinsightError("credentials_missing")
            self._chat = create_chat(self.baseline, self.settings.anthropic_api_key)
            self._counter = ClaudeTokenCounter(
                self._chat._client,
                self.baseline.generation_model,
                attempt_timeout_s=self.baseline.attempt_timeout_s,
            )
            self._generator = ClaudeGenerator(
                self.baseline, self.dispatcher, self._counter, chat=self._chat
            )
        return BaselineApplicationService(
            self.config(arm).index_config(),
            ExperimentRetriever(self, arm, True),
            self._counter,
            self._generator,
            self.pages,
            JsonlTraceRecorder(self.trace_root / "answers"),
            phase=3,
            run_fingerprint=self.config(arm).fingerprint(),
        )

    def ask_pilot(self, request, arm, *, allow_paid=False):
        from .experiment_pilot import ask_pilot

        return ask_pilot(self, request, arm, allow_paid=allow_paid)

    def close(self):
        for retriever in self._retrievers.values():
            retriever.store.client.close()
        self._retrievers.clear()
        if self._client is not None:
            self._client.close()
            self._client = None
        if self._chat is not None:
            self._chat._client.close()
            self._chat = None
        self._backend = None


def create_experiment_lab(settings, *, doc_name="AMD_2022_10K"):
    try:
        parent = CorpusManifest.model_validate_json(
            settings.manifest_path.read_text(encoding="utf-8")
        )
        corpus = parent
        if doc_name is not None:
            selected = tuple(d for d in parent.documents if d.doc_name == doc_name)
            if len(selected) != 1:
                raise FinsightError("scope_unavailable")
            corpus = CorpusManifest(
                documents=selected,
                metadata_sha256=parent.metadata_sha256,
                source_fingerprint=source_fingerprint([[d.doc_name, d.sha256] for d in selected]),
                diagnostics=tuple(d for d in parent.diagnostics if doc_name in d.doc_names),
            )
        artifact = TokenizerArtifact.load(settings.tokenizer_dir)
        baseline = BaselineConfig(source_fingerprint=corpus.source_fingerprint)
        if (
            artifact.model != baseline.tokenizer_model
            or artifact.revision != baseline.tokenizer_revision
        ):
            raise FinsightError("tokenizer_integrity")
        pages = CachedPageRepository(corpus, settings.source_pdf_dir, settings.page_cache_root)
        for doc in corpus.documents:
            pages.validate(doc.document_id)
        return ExperimentLab(
            settings, corpus, pages, LocalOffsetTokenizer(artifact), baseline=baseline
        )
    except FinsightError:
        raise
    except (OSError, ValueError):
        raise FinsightError("source_integrity") from None
